"""Views for the landing page."""

from django.db.models import F
from django.views.generic import TemplateView

from .models import Event

UPCOMING_EVENT_LIMIT = 20


class LandingView(TemplateView):
    """Render the landing page with upcoming events for signed-in visitors.

    Anonymous visitors see the same page with the login prompt, matching the
    behaviour the accounts tests expect, but no event list.
    """

    template_name = "events/landing.html"

    def get_context_data(self, **kwargs):
        """Add upcoming events, soonest first, to the template context."""
        context = super().get_context_data(**kwargs)
        context["events"] = []
        if self.request.user.is_authenticated:
            context["events"] = Event.objects.filter(
                status=Event.Status.UPCOMING
            ).order_by(F("start_time").asc(nulls_last=True), "end_time", "title")[
                :UPCOMING_EVENT_LIMIT
            ]
        return context
