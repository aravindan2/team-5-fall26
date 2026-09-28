"""Forms for registration, login, and account settings."""

from io import BytesIO
from uuid import uuid4

from PIL import Image, ImageOps
from django import forms
from django.core.files.base import ContentFile

from django.contrib.auth.forms import AuthenticationForm, UserCreationForm

from .models import User


class ProfilePhotoInput(forms.ClearableFileInput):
    """Offer photo replacement and clearing without displaying the stored URL."""

    template_name = "accounts/widgets/profile_photo_input.html"


class AccountSettingsForm(forms.ModelForm):
    """Edit public profile fields and validate and sanitize uploaded photos."""

    class Meta:
        """Expose only fields the account owner is allowed to change."""

        model = User
        fields = ("display_name", "profile_photo", "bio", "pronouns")
        widgets = {
            "profile_photo": ProfilePhotoInput(
                attrs={"accept": "image/jpeg,image/png,image/webp"}
            ),
            "bio": forms.Textarea(attrs={"rows": 4}),
        }
        help_texts = {
            "profile_photo": (
                "Optional. JPEG, PNG, or WebP; up to 5 MB and 4096 pixels per side."
            ),
        }

    def __init__(self, *args, **kwargs):
        """Allow longer upload names before replacing them with generated names."""
        super().__init__(*args, **kwargs)
        self.fields["profile_photo"].max_length = 512

    def clean_profile_photo(self):
        """Keep existing photos or re-encode new images without embedded metadata."""
        photo = self.cleaned_data.get("profile_photo")
        if not photo or not hasattr(photo, "image"):
            return photo
        if photo.size > 5 * 1024 * 1024:
            raise forms.ValidationError("Choose a photo no larger than 5 MB.")
        if photo.image.format not in {"JPEG", "PNG", "WEBP"}:
            raise forms.ValidationError("Choose a JPEG, PNG, or WebP photo.")
        if max(photo.image.size) > 4096:
            raise forms.ValidationError("Photos must be at most 4096 pixels per side.")
        try:
            photo.seek(0)
            with Image.open(photo) as source:
                normalized = ImageOps.exif_transpose(source).convert("RGB")
                normalized.thumbnail((1024, 1024))
                normalized.info.clear()
                output = BytesIO()
                normalized.save(output, format="JPEG", quality=90)
        except (OSError, ValueError) as error:
            raise forms.ValidationError("Choose a valid, undamaged photo.") from error
        return ContentFile(output.getvalue(), name=f"{uuid4().hex}.jpg")


class RegistrationForm(UserCreationForm):
    """Sign-up form for a username, email address, display name and password.

    Django's ``UserCreationForm`` already rejects usernames that differ from an
    existing one only in case, checks the password against
    ``AUTH_PASSWORD_VALIDATORS`` and saves only the password's hash.
    """

    class Meta(UserCreationForm.Meta):
        model = User
        fields = ("username", "email", "display_name")

    def clean_email(self):
        """Normalize the email address and reject one that is already registered."""
        email = User.objects.normalize_email(self.cleaned_data["email"])
        if User.objects.filter(email__iexact=email).exists():
            raise self.instance.unique_error_message(User, ["email"])
        return email


class LoginForm(AuthenticationForm):
    """Login form that takes an email address or a username, and a password."""

    error_messages = {
        **AuthenticationForm.error_messages,
        "invalid_login": (
            "Please enter a correct email or username and password. "
            "Note that the password is case-sensitive."
        ),
    }

    def __init__(self, request=None, *args, **kwargs):
        """Relabel the username field and let it fit a full email address."""
        super().__init__(request, *args, **kwargs)
        field = self.fields["username"]
        field.label = "Email or username"
        field.max_length = User._meta.get_field("email").max_length
        field.widget.attrs["maxlength"] = field.max_length
