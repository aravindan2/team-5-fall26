"""Tests for the Event model."""

from django.test import TestCase

from events.models import Event


class EventModelTests(TestCase):
    """Event rows default to upcoming and identify themselves by title."""

    def test_new_event_defaults_to_upcoming(self):
        """A freshly created event is upcoming until a sync marks it done."""
        event = Event.objects.create(guid="1", title="Yoga", content_hash="a" * 64)
        self.assertEqual(event.status, Event.Status.UPCOMING)
        self.assertEqual(event.get_status_display(), "Upcoming")
        self.assertEqual(Event.Status.DONE.value, "done")

    def test_str_returns_the_title(self):
        """Admin listings show the event title."""
        event = Event.objects.create(
            guid="2", title="Birdwatching", content_hash="b" * 64
        )
        self.assertEqual(str(event), "Birdwatching")

    def test_default_ordering_is_chronological(self):
        """Events are ordered by start time, then end time, then title."""
        self.assertEqual(Event._meta.ordering, ["start_time", "end_time", "title"])
