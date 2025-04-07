from __future__ import annotations
from .object_type import Duration, Intangible
from typing import TYPE_CHECKING
from enum import Enum

if TYPE_CHECKING:
    from .data_type import Date


class RepeatFrequency(Enum):
    Daily = "Daily"
    Weekly = "Weekly"
    Monthly = "Monthly"
    Yearly = "Yearly"


class Schedule(Intangible):
    __description__ = "A schedule defines a repeating time period used to describe a regularly occurring Event. At a minimum a schedule will specify repeatFrequency which describes the interval between occurrences of the event. Additional information can be provided to specify the schedule more precisely. This includes identifying the day(s) of the week or month when the recurring event will take place, in addition to its start and end time. Schedules may also have start and end dates to indicate when they are active, e.g. to define a limited calendar of events."
    __schema_properties__ = Intangible.__schema_properties__ | {
        "byDay": ['r', "DayOfWeek", "Text"],
        "byMonth": ['r', "Integer"],
        "byMonthDay": ['r', "Integer"],
        "byMonthWeek": ['r', "Integer"],
        "duration": "Duration",
        "endDate": ["Date", "DateTime"],
        "endTime": ["DateTime", "Time"],
        "exceptDate": ["Date", "DateTime"],
        "repeatCount": "Integer",
        "repeatFrequency": ["RepeatFrequency", "Duration", "Text"],
        "scheduleTimezone": "Text",
        "startDate": ["Date", "DateTime"],
        "startTime": ["DateTime", "Time"]
    }
    __gsc_required_properties__ = [
        "repeatCount",
        "repeatFrequency"
    ]

    def __init__(self,
                 repeat_count: int,
                 repeat_frequency: RepeatFrequency,
                 duration: Duration | None = None,
                 start_date: Date | str | None = None,
                 end_date: Date | str | None = None, **kwargs) -> None:
        super().__init__(
            repeat_count=repeat_count,
            repeat_frequency=repeat_frequency,
            duration=duration,
            start_date=start_date,
            end_date=end_date,
            **kwargs
        )
