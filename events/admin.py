"""Admin configuration for imported events."""

from django.contrib import admin

from .models import Event


@admin.register(Event)
class EventAdmin(admin.ModelAdmin):
    """Show the fields the sync manages in a readable, searchable list."""

    list_display = ("title", "start_time", "end_time", "status")
    list_filter = ("status",)
    search_fields = ("title", "location", "park_names")
    ordering = ("start_time",)
