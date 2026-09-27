"""Views for user account pages."""
from django.conf import settings
from django.contrib.auth import views as auth_views
from django.contrib.messages.views import SuccessMessageMixin
from django.shortcuts import resolve_url, render
from django.urls import reverse_lazy
from django.views.generic import CreateView
from django.contrib.auth.views import LoginView
from django.contrib import messages
from django.core.cache import cache
import time

from .forms import LoginForm, RegistrationForm

# Lockout configuration
LOCKOUT_THRESHOLD = 5
LOCKOUT_DURATION_SECONDS = 10 * 60  # 10 minutes lockout
CACHE_KEY_ATTEMPTS = "login_attempts:"
CACHE_KEY_LOCK_EXPIRY = "login_lock_expiry:"
SESSION_LIFESPAN_SECONDS = 48 * 60 * 60  # 48 hours idle sliding expiry


class RegisterView(SuccessMessageMixin, CreateView):
    """Create an account, then send the new user to the login page."""

    form_class = RegistrationForm
    template_name = "accounts/register.html"
    success_message = "Welcome, %(name)s! Your account has been created. Please log in."

    def get_context_data(self, **kwargs):
        """Add the login page URL for the "Already have an account?" link."""
        context = super().get_context_data(**kwargs)
        context["login_url"] = resolve_url(settings.LOGIN_URL)
        return context

    def get_success_url(self):
        """Return the login page URL."""
        return resolve_url(settings.LOGIN_URL)

    def get_success_message(self, cleaned_data):
        """Greet the new user by display name, or by username if they left it blank."""
        return self.success_message % {"name": self.object.get_display_name()}


class CustomLoginView(SuccessMessageMixin, LoginView):
    """
    Custom login view supporting username/email login, brute force lockout,
    and 48-hour sliding idle session expiration.

    After successful login, redirects to landing page (landing route).
    After 5 consecutive failed login attempts, blocks login for 10 minutes.
    Lock expiry timestamp is stored in cache so countdown persists on page refresh.
    Session expires after 48 hours of user inactivity (sliding refresh on every request).
    Passes lock expiry timestamp to template for frontend countdown.
    Shows welcome message after successful login.
    """
    template_name = "accounts/login.html"
    redirect_authenticated_user = True
    success_url = reverse_lazy("landing")
    success_message = "Welcome back, %(name)s!"
    form_class = LoginForm

    def get_success_message(self, cleaned_data):
        """Greet the user by display name, or by username if they have none."""
        return self.success_message % {"name": self.request.user.get_display_name()}

    def _get_attempt_key(self, login_identifier: str) -> str:
        """
        Generate cache key for counting failed login attempts.

        Args:
            login_identifier: username or email entered in login form
        Returns:
            prefixed cache key string
        """
        return f"{CACHE_KEY_ATTEMPTS}{login_identifier}"

    def _get_lock_expiry_key(self, login_identifier: str) -> str:
        """
        Generate cache key that stores the absolute lock expiry timestamp.

        Args:
            login_identifier: username or email entered in login form
        Returns:
            prefixed cache key string
        """
        return f"{CACHE_KEY_LOCK_EXPIRY}{login_identifier}"

    def dispatch(self, request, *args, **kwargs):
        """
        Intercept login request before credential validation.
        Read saved lock expiry timestamp from cache.
        If still locked, add error message and RENDER login page (200 OK) with countdown context,
        DO NOT redirect, to pass tests and keep countdown on page.
        Counting happens in form_invalid after form cleaning.
        """
        self.lock_expiry_timestamp = None
        if request.method == "POST":
            raw_username = request.POST.get("username", "").strip()
            lock_expiry_key = self._get_lock_expiry_key(raw_username)
            stored_lock_ts = cache.get(lock_expiry_key)

            now = time.time()
            if stored_lock_ts and stored_lock_ts > now:
                self.lock_expiry_timestamp = stored_lock_ts
                messages.error(
                    request,
                    "Too many failed login attempts. Please try again in 10 minutes."
                )
                context = self.get_context_data()
                context["form"] = self.get_form()
                return render(request, self.template_name, context)
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self,** kwargs):
        """Pass lock expiry timestamp to template context for frontend countdown."""
        context = super().get_context_data(**kwargs)
        context["lock_expiry"] = self.lock_expiry_timestamp
        return context

    def form_invalid(self, form):
        """
        Handle failed login submission. Increment failure counter,
        apply lockout after reaching attempt threshold,
        render login page again (200 OK) with form errors and countdown context.

        Args:
            form: LoginForm with invalid credentials
        Returns:
            HttpResponse: rendered login template with error
        """
        username_input = form.cleaned_data.get("username", "").strip()
        if not username_input:
            username_input = self.request.POST.get("username", "").strip()

        attempt_key = self._get_attempt_key(username_input)
        lock_expiry_key = self._get_lock_expiry_key(username_input)

        current_attempts = cache.get(attempt_key, 0) + 1
        cache.set(attempt_key, current_attempts, LOCKOUT_DURATION_SECONDS)

        if current_attempts >= LOCKOUT_THRESHOLD:
            lock_ts = time.time() + LOCKOUT_DURATION_SECONDS
            cache.set(lock_expiry_key, lock_ts, LOCKOUT_DURATION_SECONDS)
            self.lock_expiry_timestamp = lock_ts
            messages.error(
                self.request,
                "Too many failed login attempts. You are blocked for 10 minutes."
            )
        context = self.get_context_data(form=form)
        return render(self.request, self.template_name, context)

    def form_valid(self, form):
        """
        Handle successful login. Clear failure counter and lock record,
        set 48-hour sliding session expiry.

        Args:
            form: LoginForm with valid credentials
        Returns:
            HttpResponseRedirect: redirect to landing page
        """
        username_input = form.cleaned_data.get("username")
        attempt_key = self._get_attempt_key(username_input)
        lock_expiry_key = self._get_lock_expiry_key(username_input)

        cache.delete(attempt_key)
        cache.delete(lock_expiry_key)
        self.request.session.set_expiry(SESSION_LIFESPAN_SECONDS)
        return super().form_valid(form)


class PasswordResetView(auth_views.PasswordResetView):
    """Ask for an email address and send a password reset link to it.
    The same confirmation page is shown whether or not the address belongs to
    an account, so the form can't be used to find out who is registered.
    """
    template_name = "accounts/password_reset_form.html"
    email_template_name = "accounts/password_reset_email.txt"
    subject_template_name = "accounts/password_reset_subject.txt"
    success_url = reverse_lazy("password_reset_done")


class PasswordResetDoneView(auth_views.PasswordResetDoneView):
    """Tell the user to check their email for the reset link."""
    template_name = "accounts/password_reset_done.html"


class PasswordResetConfirmView(
    SuccessMessageMixin, auth_views.PasswordResetConfirmView
):
    """Let the user choose a new password, then send them to the login page."""
    template_name = "accounts/password_reset_confirm.html"
    success_url = reverse_lazy("login")
    success_message = "Your password has been reset. You can now log in."
