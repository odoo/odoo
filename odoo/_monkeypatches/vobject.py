from zoneinfo import ZoneInfo
from vobject import icalendar


def patch_module():
    original_pickTzid = icalendar.TimezoneComponent.pickTzid
    if original_pickTzid(ZoneInfo("Australia/Perth")) == "Australia/Perth":
        return

    @staticmethod
    def _patched_pickTzid(tzinfo, allowUTC=False):
        # Extract IANA identifier from Python 3.9+ ZoneInfo objects.
        if tzinfo is not None:
            try:
                key = tzinfo.key
            except AttributeError:
                pass
            else:
                if key:
                    if not allowUTC and icalendar.tzinfo_eq(tzinfo, icalendar.utc):
                        return None
                    return key

        return original_pickTzid(tzinfo, allowUTC)

    icalendar.TimezoneComponent.pickTzid = _patched_pickTzid
