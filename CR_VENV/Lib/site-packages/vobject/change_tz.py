"""Translate an ics file's events to a different timezone."""

from optparse import OptionParser
from vobject import icalendar, base

try:
    import PyICU
except:
    PyICU = None

from datetime import datetime


def change_tz(cal, new_timezone, default, utc_only=False, utc_tz=icalendar.utc):
    """
    Change the timezone of the specified component.

    Args:
        cal (Component): the component to change
        new_timezone (tzinfo): the timezone to change to
        default (tzinfo): a timezone to assume if the dtstart or dtend in cal
            doesn't have an existing timezone
        utc_only (bool): only convert dates that are in utc
        utc_tz (tzinfo): the tzinfo to compare to for UTC when processing
            utc_only=True
    """

    for vevent in getattr(cal, 'vevent_list', []):
        start = getattr(vevent, 'dtstart', None)
        end = getattr(vevent, 'dtend', None)
        for node in (start, end):
            if node:
                dt = node.value
                if (isinstance(dt, datetime) and
                        (not utc_only or dt.tzinfo == utc_tz)):
                    if dt.tzinfo is None:
                        dt = dt.replace(tzinfo=default)
                    node.value = dt.astimezone(new_timezone)


def main():
    options, args = get_options()
    if PyICU is None:
        print("Failure. change_tz requires PyICU, exiting")
    elif options.list:
        for tz_string in PyICU.TimeZone.createEnumeration():
            print(tz_string)
    elif args:
        utc_only = options.utc
        if utc_only:
            which = "only UTC"
        else:
            which = "all"
        print("Converting {0!s} events".format(which))
        ics_file = args[0]
        if len(args) > 1:
            timezone = PyICU.ICUtzinfo.getInstance(args[1])
        else:
            timezone = PyICU.ICUtzinfo.default
        print("... Reading {0!s}".format(ics_file))
        cal = base.readOne(open(ics_file))
        change_tz(cal, timezone, PyICU.ICUtzinfo.default, utc_only)

        out_name = ics_file + '.converted'
        print("... Writing {0!s}".format(out_name))

        with open(out_name, 'wb') as out:
            cal.serialize(out)

        print("Done")


version = "0.1"


def get_options():
    # Configuration options

    usage = """usage: %prog [options] ics_file [timezone]"""
    parser = OptionParser(usage=usage, version=version)
    parser.set_description("change_tz will convert the timezones in an ics file. ")

    parser.add_option("-u", "--only-utc", dest="utc", action="store_true",
                      default=False, help="Only change UTC events.")
    parser.add_option("-l", "--list", dest="list", action="store_true",
                      default=False, help="List available timezones")

    (cmdline_options, args) = parser.parse_args()
    if not args and not cmdline_options.list:
        print("error: too few arguments given")
        print
        print(parser.format_help())
        return False, False

    return cmdline_options, args

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("Aborted")
