"""URL routes for the accounts app."""
from django.urls import path

from django.contrib.auth.views import (
    LogoutView,
    PasswordResetCompleteView,
)

from . import views
from .views import RegisterView, CustomLoginView

urlpatterns = [
    path("register/", RegisterView.as_view(), name="register"),
    path("login/", CustomLoginView.as_view(), name="login"),
    path("logout/", LogoutView.as_view(next_page="landing"), name="logout"),

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
        PasswordResetCompleteView.as_view(),
        name="password_reset_complete",
    ),
]
