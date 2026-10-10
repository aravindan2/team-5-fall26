"""Views for the landing page and public event search."""

from django.db.models import F
from django.views.generic import ListView, TemplateView

from .models import Event
from .search import search_events

UPCOMING_EVENT_LIMIT = 20
SEARCH_PAGE_SIZE = 20


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


class SearchView(ListView):
    """Let any visitor search upcoming events using PostgreSQL full-text search."""

    template_name = "events/search.html"
    context_object_name = "events"
    paginate_by = SEARCH_PAGE_SIZE

    def get_queryset(self):
        """Return ranked matches, or an empty queryset until a term is supplied."""
        self.query = self.request.GET.get("q", "").strip()
        if not self.query:
            return Event.objects.none()
        return search_events(
            Event.objects.filter(status=Event.Status.UPCOMING), self.query
        )

    def get_context_data(self, **kwargs):
        """Keep the search term available for the form and pagination links."""
        context = super().get_context_data(**kwargs)
        context["query"] = self.query
        return context
