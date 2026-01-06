from abc import ABC, abstractmethod

from odoo.tools import date_utils

from .generator import Generator


class Temporal(Generator, ABC):
    """
    Base class for date/datetime generators over a ``[start, end]`` range.

    Subclasses define the time unit, format, and default range bounds.
    """
    time_unit: str
    format: str
    default_start: str
    default_end: str

    def __init__(self, start: str | None = None, end: str | None = None, **kwargs):
        """Parse date bounds accepted by Odoo date utilities.

        :param start: Lower bound expression, defaulting to the subclass range start.
        :param end: Upper bound expression, defaulting to the subclass range end.
        """
        super().__init__(**kwargs)
        self.start = date_utils.parse_date(start or self.default_start, self.env)
        self.end = date_utils.parse_date(end or self.default_end, self.env)

    def _next(self, known_vals):
        offset = self.distribution.sample_discrete(0, self.delta)
        return date_utils.add(self.start, **{self.time_unit: offset}).strftime(self.format)

    @property
    @abstractmethod
    def delta(self):
        ...

    @classmethod
    def convert_to_kwargs(cls, attrs):
        kwargs = super().convert_to_kwargs(attrs)
        kwargs.update(**{k: v for k, v in attrs.items() if k in ('start', 'end')})
        return kwargs


class Date(Temporal):
    """Generate random dates between ``start`` and ``end``."""
    name = 'temporal.date'
    allowed_field_types = ('date', 'datetime', 'virtual')
    time_unit = 'days'
    format = '%Y-%m-%d'
    default_start = 'today -5y'
    default_end = 'today'

    @property
    def delta(self):
        return (self.end - self.start).days


class Datetime(Temporal):
    """Generate random datetimes between ``start`` and ``end``."""
    name = 'temporal.datetime'
    allowed_field_types = ('datetime', 'virtual')
    time_unit = 'seconds'
    format = '%Y-%m-%d %H:%M:%S'
    default_start = 'now -5y'
    default_end = 'now'

    @property
    def delta(self):
        return int((self.end - self.start).total_seconds())
