from __future__ import annotations
import re

from datetime import datetime, date, time
from typing import Any
from urllib.parse import urlparse


class DataType:
    """Represents a generic DataType in the schema.org hierarchy."""

    def __init__(self, value) -> None:
        """
        Initialize a DataType instance.

        Args:
            value: The value of the DataType.
        """
        self.value = value

    def to_dict(self) -> Any:
        """
        Generate the JSON-LD representation of the DataType.

        Returns:
            The value as a primitive type.
        """
        return self.value


class Boolean(DataType):
    def __init__(self, value: bool) -> None:
        if not isinstance(value, bool):
            raise TypeError("Boolean data type must be True or False")
        super().__init__(value)


class Number(DataType):
    """Represents a Number (integer or float) in schema.org."""

    def __init__(self, value: float) -> None:
        if not isinstance(value, (int, float)):
            raise TypeError("Number value must be an integer or float.")
        super().__init__(value)


class Text(DataType):
    """Represents a Text (string) in schema.org."""

    def __init__(self, value: str) -> None:
        if not isinstance(value, str):
            raise TypeError("Text value must be a string.")
        super().__init__(value)


class Date(DataType):
    """Represents a Date in schema.org (ISO 8601 format)."""

    def __init__(self, value: str | date) -> None:
        if isinstance(value, date):
            # If it's already a date object, convert it to an ISO 8601 string
            self.value = value.isoformat()
        elif isinstance(value, str):
            # If it's a string, validate it as an ISO 8601 date string
            self._validate_iso8601_date(value)
            self.value = value
        else:
            raise TypeError("Value must be a date object or a string in ISO 8601 format.")

        super().__init__(self.value)

    def _validate_iso8601_date(self, value: str) -> None:
        """
        Validates if the string is in ISO 8601 date format (YYYY-MM-DD).
        Raises:
            ValueError: If the value is invalid
        """
        iso8601_date_regex = r"^\d{4}-\d{2}-\d{2}$"
        if not re.match(iso8601_date_regex, value):
            raise ValueError(f"Invalid ISO 8601 date format: {value}")


class Time(DataType):
    """Represents a Time in schema.org (ISO 8601 format)."""

    def __init__(self, value: str | time) -> None:
        if isinstance(value, time):
            # If it's already a time object, convert it to an ISO 8601 string
            self.value = value.isoformat()
        elif isinstance(value, str):
            # If it's a string, validate it as an ISO 8601 time string
            self._validate_iso8601_time(value)
            self.value = value
        else:
            raise TypeError("Value must be a time object or a string in ISO 8601 format.")

        super().__init__(self.value)

    def _validate_iso8601_time(self, value: str) -> None:
        """
        Validates if the string is in ISO 8601 time format (HH:MM:SS).
        Raises:
            ValueError: If invalid format
        """
        iso8601_time_regex = r"^\d{2}:\d{2}:\d{2}$"
        if not re.match(iso8601_time_regex, value):
            raise ValueError(f"Invalid ISO 8601 time format: {value}")


class DateTime(DataType):
    """Represents a DateTime in schema.org (ISO 8601 format)."""

    def __init__(self, value: str | datetime) -> None:
        if isinstance(value, datetime):
            # If it's already a datetime object, convert it to an ISO 8601 string
            self.value = value.isoformat()
        elif isinstance(value, str):
            # If it's a string, validate it as an ISO 8601 date string
            self._validate_iso8601(value)
            self.value = value
        else:
            raise TypeError("Value must be a datetime object or a string in ISO 8601 format.")

        super().__init__(self.value)

    def _validate_iso8601(self, value: str) -> None:
        """
        Validates if the string is in ISO 8601 format.
        Raises:
            ValueError: If invalid format
        """
        iso8601_regex = (
            r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?(?:Z|[+-]\d{2}:\d{2})?$"
        )
        if not re.match(iso8601_regex, value):
            raise ValueError(f"Invalid ISO 8601 format: {value}")


class URL(Text):
    def __init__(self, value: str) -> None:
        """
        Initialize a URL instance with validation.

        Args:
            value (str): The URL string.

        Raises:
            ValueError: If the URL is not valid.
        """
        value = self._add_protocol_if_missing(value)
        if not self._is_valid_url(value):
            raise ValueError(f"Invalid URL: {value}")

        super().__init__(value)

    @staticmethod
    def _add_protocol_if_missing(url: str) -> str:
        """
        Add 'http://' to the URL if it does not already have a protocol.
        Returns:
            str: Corrected url
        """
        parsed = urlparse(url)
        if not parsed.scheme:
            return "http://" + url
        return url

    @staticmethod
    def _is_valid_url(url: str) -> bool:
        """
        Validate a URL using urllib.
        Returns:
            bool: True if the url is valid
        """
        parsed = urlparse(url)
        return bool(parsed.netloc)
