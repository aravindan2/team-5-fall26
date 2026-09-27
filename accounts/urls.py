"""URL routes for the accounts app."""
from django.contrib.auth.views import LogoutView
from django.urls import path

from . import views
from .views import RegisterView, CustomLoginView


urlpatterns = [
    path("register/", RegisterView.as_view(), name="register"),
    # Use CustomLoginView with brute force lockout and 48h session
    path("login/", CustomLoginView.as_view(), name="login"),
    # Logout redirect to landing page
    path("logout/", LogoutView.as_view(next_page="landing"), name="logout"),

    # Password reset routes (using views' reset classes)
    path(
        "password-reset/",
        views.PasswordResetView.as_view(),
        name="password_reset",
    ),
    path(
        "password-reset/done/",
        views.PasswordResetDoneView.as_view(),
        name="password_reset_done",
    ),
    path(
        "reset/<uidb64>/<token>/",
        views.PasswordResetConfirmView.as_view(),
        name="password_reset_confirm",
    ),
    path(
        "password-reset/complete/",
        views.PasswordResetCompleteView.as_view(),
        name="password_reset_complete",
    ),
]
