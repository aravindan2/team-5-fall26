"""Data models for NYC Parks events imported from the city's open data feed."""

from django.db import models


class Event(models.Model):
    """One NYC Parks event, copied from the open data feed.

    The feed only publishes a rolling two-week window, so this table is the
    durable copy of the data: rows stay in the database after they disappear
    from the feed and are marked done once their end time has passed.

    ``content_hash`` fingerprints the imported content so an hourly sync can
    skip rows that have not really changed, and ``guid`` is the unique
    identifier the feed uses for each event.
    """

    class Status(models.TextChoices):
        """Lifecycle of an event as tracked by the hourly sync."""

        UPCOMING = "upcoming", "Upcoming"
        DONE = "done", "Done"

    guid = models.CharField("source id", max_length=64, unique=True, db_index=True)
    title = models.CharField("title", max_length=300)
    description = models.TextField("description", blank=True)
    start_time = models.DateTimeField("start time", null=True, blank=True)
    end_time = models.DateTimeField("end time", null=True, blank=True)
    location = models.CharField("location", max_length=300, blank=True)
    park_names = models.CharField("park names", max_length=300, blank=True)
    park_ids = models.CharField("park ids", max_length=100, blank=True)
    categories = models.CharField("categories", max_length=500, blank=True)
    latitude = models.FloatField("latitude", null=True, blank=True)
    longitude = models.FloatField("longitude", null=True, blank=True)
    event_url = models.URLField("event URL", max_length=500, blank=True)
    registration_url = models.URLField("registration URL", max_length=500, blank=True)
    image_url = models.URLField("image URL", max_length=500, blank=True)
    instructor = models.CharField("instructor", max_length=100, blank=True)
    contact_phone = models.CharField("contact phone", max_length=50, blank=True)
    status = models.CharField(
        "status",
        max_length=10,
        choices=Status.choices,
        default=Status.UPCOMING,
        db_index=True,
    )
    content_hash = models.CharField("content hash", max_length=64)
    source_version = models.CharField("source version", max_length=64, blank=True)
    first_seen_at = models.DateTimeField("first seen at", auto_now_add=True)
    last_synced_at = models.DateTimeField("last synced at", null=True, blank=True)
    updated_at = models.DateTimeField("updated at", auto_now=True)

    class Meta:
        """List events chronologically by default."""

        ordering = ["start_time", "end_time", "title"]

    def __str__(self):
        """Return the event title for admin listings and debug output."""
        return self.title
