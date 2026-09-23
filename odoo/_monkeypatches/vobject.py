import vobject.icalendar
from zoneinfo import ZoneInfo


def patch_module():
    original_pickTzid = vobject.icalendar.TimezoneComponent.pickTzid
    if original_pickTzid(ZoneInfo("Australia/Perth")) == "Australia/Perth":
        return

    to_unicode = vobject.icalendar.toUnicode

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
                    if not allowUTC and key == 'UTC':
                        return None
                    return to_unicode(key)

        return original_pickTzid(tzinfo, allowUTC)

    vobject.icalendar.TimezoneComponent.pickTzid = _patched_pickTzid
