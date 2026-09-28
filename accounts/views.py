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
        """
        Pass login page URL to template for "Already have an account?" link.
        """
        context = super().get_context_data(**kwargs)
        context["login_url"] = resolve_url(settings.LOGIN_URL)
        return context

    def get_success_url(self):
        """Return the login page URL."""
        return resolve_url(settings.LOGIN_URL)

    def get_success_message(self, cleaned_data):
        """Greet the new user by display name, or by username if they left it blank."""
        return self.success_message % {"name": self.object.get_display_name()}


class CustomLoginView(LoginView):
    """
    Custom login view supporting username/email login, brute force lockout,
    and 48-hour sliding idle session expiration.

    After successful login, redirects to landing page (landing route).
    After 5 consecutive failed login attempts, blocks login for 10 minutes.
    Lock expiry timestamp is stored in cache so countdown persists on page refresh.
    Session expires after 48 hours of user inactivity (sliding refresh on every request).
    Passes lock expiry timestamp and locked login identifier to template for frontend countdown.
    Welcome message is shown on landing page AFTER login, not on login page.
    """
    template_name = "accounts/login.html"
    redirect_authenticated_user = True
    success_url = reverse_lazy("landing")
    form_class = LoginForm

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.lock_expiry_timestamp = None
        self.locked_identifier = None

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
        If still locked, render login page with countdown context.
        """
        self.lock_expiry_timestamp = None
        self.locked_identifier = None
        if request.method == "POST":
            raw_username = request.POST.get("username", "").strip()
            lock_expiry_key = self._get_lock_expiry_key(raw_username)
            stored_lock_ts = cache.get(lock_expiry_key)

            now = time.time()
            if stored_lock_ts and stored_lock_ts > now:
                self.lock_expiry_timestamp = stored_lock_ts
                self.locked_identifier = raw_username
                context = self.get_context_data()
                context["form"] = self.get_form()
                # Pass locked account identifier to template
                context["locked_identifier"] = self.locked_identifier
                return render(request, self.template_name, context)
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self,** kwargs):
        """Pass lock expiry timestamp and locked identifier to template context for frontend countdown."""
        context = super().get_context_data(**kwargs)
        context["lock_expiry"] = self.lock_expiry_timestamp
        context["locked_identifier"] = self.locked_identifier
        return context

    def form_valid(self, form):
        """
        Run when login credentials are correct.
        Clear failed attempt counter and lock record from cache.
        Set sliding session timeout for 48 hours.
        """
        # Clear failed attempts and lock key for this identifier
        username_input = form.cleaned_data.get("username", "").strip()
        attempt_key = self._get_attempt_key(username_input)
        lock_expiry_key = self._get_lock_expiry_key(username_input)
        cache.delete(attempt_key)
        cache.delete(lock_expiry_key)

        # 48h sliding session expiry
        self.request.session.set_expiry(SESSION_LIFESPAN_SECONDS)
        return super().form_valid(form)

    def form_invalid(self, form):
        """
        Handle failed login submission.
        Increment failure counter and apply lockout after reaching threshold.
        Pass remaining attempts, lock expiry and locked identifier to the template.

        Args:
            form: LoginForm with invalid credentials
        Returns:
            HttpResponse: rendered login page with error context
        """
        username_input = form.cleaned_data.get("username", "").strip()
        if not username_input:
            username_input = self.request.POST.get("username", "").strip()

        attempt_key = self._get_attempt_key(username_input)
        lock_expiry_key = self._get_lock_expiry_key(username_input)

        current_attempts = cache.get(attempt_key, 0) + 1
        cache.set(attempt_key, current_attempts, LOCKOUT_DURATION_SECONDS)

        remaining_attempts = LOCKOUT_THRESHOLD - current_attempts

        if current_attempts >= LOCKOUT_THRESHOLD:
            lock_ts = time.time() + LOCKOUT_DURATION_SECONDS
            cache.set(lock_expiry_key, lock_ts, LOCKOUT_DURATION_SECONDS)
            self.lock_expiry_timestamp = lock_ts
            self.locked_identifier = username_input
            remaining_attempts = 0
        else:
            self.lock_expiry_timestamp = None
            self.locked_identifier = None

        context = self.get_context_data(form=form)
        context["remaining_attempts"] = remaining_attempts
        context["current_attempts"] = current_attempts
        return render(self.request, self.template_name, context)


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
