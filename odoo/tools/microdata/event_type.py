from __future__ import annotations
from .core.object_type import Thing, Place, VirtualLocation, ImageObject, Offer, Person, Organization
from enum import Enum
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .core.data_type import DateTime, Date, URL


class EventAttendanceModeEnumeration(Enum):
    Offline = "https://schema.org/OfflineEventAttendanceMode"
    Online = "https://schema.org/OnlineEventAttendanceMode"
    Mixed = "https://schema.org/MixedEventAttendanceMode"


class EventStatusType(Enum):
    Cancelled = "https://schema.org/EventCancelled"
    MovedOnline = "https://schema.org/EventMovedOnline"
    Postponed = "https://schema.org/EventPostponed"
    Rescheduled = "https://schema.org/EventRescheduled"
    Scheduled = "https://schema.org/EventScheduled"


class Event(Thing):
    __description__ = """
        An event happening at a certain time and location, such as a concert,
        lecture, or festival. Ticketing information may be added via the offers
        property. Repeated events may be structured as separate Event objects.
    """
    __schema_properties__ = Thing.__schema_properties__ | {
        "about": ['r', "Thing"],
        "actor": ['r', "PerformingGroup", "Person"],
        "aggregateRating": "AgreggateRating",
        "attendee": ['r', "Organization", "Person"],
        "audience": ['r', "Audience"],
        "composer": ['r', "Organization", "Person"],
        "contributor": ['r', "Organization", "Person"],
        "director": ['r', "Person"],
        "doorTime": ["DateTime", "Time"],
        "duration": ["Duration"],
        "endDate": ["Date", "DateTime"],
        "eventAttendanceMode": ["EventAttendanceModeEnumeration"],
        "eventSchedule": "Schedule",
        "eventStatus": "EventStatusType",
        "funder": ['r', "Organization", "Person"],
        "funding": ["Grant"],
        "inLanguage": ['r', "Language", "Text"],
        "isAccessibleForFree": "Boolean",
        "keywords": ['r', "DefinedTerm", "Text", "URL"],
        "location": ["Place", "PostalAddress", "Text", "VirtualLocation"],
        "maximumAttendeeCapacity": "Integer",
        "maximumPhysicalAttendeeCapacity": "Integer",
        "maximumVirtualAttendeeCapacity": "Integer",
        "offers": ['r', "Offer", "Demand"],
        "organizer": ['r', "Person", "Organization"],
        "performer": ['r', "Person", "Organization"],
        "previousStartDate": ["Date", "DateTime"],
        "recordedIn": "CreativeWork",
        "remainingAttendeeCapacity": "Integer",
        "review": "Review",
        "sponsor": ['r', "Organization", "Person"],
        "startDate": ["Date", "DateTime"],
        "subEvent": ['r', "Event"],
        "superEvent": "Event",
        "translator": ['r', "Person", "Organization"],
        "typicalAgeRange": "Text",
        "workFeatured": ['r', "CreativeWork"],
        "workPerformed": ['r', "CreativeWork"]
    }
    __gsc_required_properties__ = [
        'location',
        'location.address',
        'name',
        'startDate'
    ]

    def __init__(self,
                 name: str | None = None,
                 location: Place | VirtualLocation | list[Place | VirtualLocation] | None = None,
                 start_date: DateTime | Date | None = None,
                 description: str | None = None,
                 end_date: DateTime | Date | str | None = None,
                 event_attendance_mode: EventAttendanceModeEnumeration = None,
                 event_status: EventStatusType = None,
                 image: ImageObject | URL | list[ImageObject | URL] = None,
                 offers: Offer | list[Offer] = None,
                 organizer: Person | Organization = None,
                 performer: Person | list[Person] = None,
                 previous_start_date: DateTime | Date | str | None = None,
                 **kwargs) -> None:
        super().__init__(
            name=name,
            location=location,
            start_date=start_date,
            description=description,
            end_date=end_date,
            event_attendance_mode=event_attendance_mode,
            event_status=event_status,
            image=image,
            offers=offers,
            organizer=organizer,
            performer=performer,
            previous_start_date=previous_start_date,
            **kwargs
        )
        self._dict = self.to_dict()

    def gsc_validate(self) -> None:
        if self.event_attendance_mode == EventAttendanceModeEnumeration.Online:
            if not self.get_property('location.url', self._dict):
                raise ValueError("The URL of the online event is required if your event is happening online.")
        elif self.event_attendance_mode == EventAttendanceModeEnumeration.Offline:
            if not self.get_property('location.address', self._dict):
                raise ValueError("The venue's detailed street address is required for events that take place at a physical location.")
        else:
            if not self.get_property('location.url', self._dict) and not self.get_property('location.address', self._dict):
                raise ValueError("If an event has a mix of online and physical location components, include both online and physical nested location properties")
        return True
