"""Custom authentication backends for accounts app."""
from django.contrib.auth import get_user_model
from django.contrib.auth.backends import ModelBackend
from django.db.models import Q

User = get_user_model()


class EmailOrUsernameModelBackend(ModelBackend):
    """
    Custom authentication backend allowing users to log in
    using either their username OR registered email address.

    Inherits Django's ModelBackend, maintains standard password validation.
    Handles case-insensitive email matching and case-insensitive username matching,
    avoids MultipleObjectsReturned error when multiple users match the login identifier.
    """
    def authenticate(self, request, username=None, password=None, **kwargs):
        """
        Authenticate user by matching input against username or email field.
        Username and email matching are both case-insensitive.
        Iterate over all matched users and validate password one by one.

        Args:
            request: Django HttpRequest object
            username: user-supplied login identifier (username or email string)
            password: user-supplied plaintext password
        Returns:
            User object if credentials valid and user is active; None otherwise
        """
        if username is None or password is None:
            return None

        # username __iexact (case-insensitive), email __iexact
        candidate_users = User.objects.filter(
            Q(username__iexact=username) | Q(email__iexact=username)
        )

        for user in candidate_users:
            if user.check_password(password) and self.user_can_authenticate(user):
                return user
