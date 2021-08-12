import os
import re
import pytz

_cache_tz = None

def _tz_from_env(tzenv):
    if tzenv[0] == ':':
        tzenv = tzenv[1:]

    # TZ specifies a file
    if os.path.exists(tzenv):
        with open(tzenv, 'rb') as tzfile:
            return pytz.tzfile.build_tzinfo('local', tzfile)

    # TZ specifies a zoneinfo zone.
    try:
        tz = pytz.timezone(tzenv)
        # That worked, so we return this:
        return tz
    except pytz.UnknownTimeZoneError:
        raise pytz.UnknownTimeZoneError(
            "tzlocal() does not support non-zoneinfo timezones like %s. \n"
            "Please use a timezone in the form of Continent/City")


def _try_tz_from_env():
    tzenv = os.environ.get('TZ')
    if tzenv:
        try:
            return _tz_from_env(tzenv)
        except pytz.UnknownTimeZoneError:
            pass


def _get_localzone(_root='/'):
    """Tries to find the local timezone configuration.

    This method prefers finding the timezone name and passing that to pytz,
    over passing in the localtime file, as in the later case the zoneinfo
    name is unknown.

    The parameter _root makes the function look for files like /etc/localtime
    beneath the _root directory. This is primarily used by the tests.
    In normal usage you call the function without parameters."""

#     tzenv = _try_tz_from_env()
#     if tzenv:
#         return tzenv

    # Now look for distribution specific configuration files
    # that contain the timezone name.
    for configfile in ('etc/timezone', 'var/db/zoneinfo'):
        tzpath = os.path.join(_root, configfile)
        if os.path.exists(tzpath):
            with open(tzpath, 'rb') as tzfile:
                data = tzfile.read()

                # Issue #3 was that /etc/timezone was a zoneinfo file.
                # That's a misconfiguration, but we need to handle it gracefully:
                if data[:5] == 'TZif2':
                    continue

                etctz = data.strip().decode()
                # Get rid of host definitions and comments:
                if ' ' in etctz:
                    etctz, dummy = etctz.split(' ', 1)
                if '#' in etctz:
                    etctz, dummy = etctz.split('#', 1)
                return pytz.timezone(etctz.replace(' ', '_'))

    # CentOS has a ZONE setting in /etc/sysconfig/clock,
    # OpenSUSE has a TIMEZONE setting in /etc/sysconfig/clock and
    # Gentoo has a TIMEZONE setting in /etc/conf.d/clock
    # We look through these files for a timezone:

    zone_re = re.compile('\s*ZONE\s*=\s*\"')
    timezone_re = re.compile('\s*TIMEZONE\s*=\s*\"')
    end_re = re.compile('\"')

    for filename in ('etc/sysconfig/clock', 'etc/conf.d/clock'):
        tzpath = os.path.join(_root, filename)
        if not os.path.exists(tzpath):
            continue
        with open(tzpath, 'rt') as tzfile:
            data = tzfile.readlines()

        for line in data:
            # Look for the ZONE= setting.
            match = zone_re.match(line)
            if match is None:
                # No ZONE= setting. Look for the TIMEZONE= setting.
                match = timezone_re.match(line)
            if match is not None:
                # Some setting existed
                line = line[match.end():]
                etctz = line[:end_re.search(line).start()]

                # We found a timezone
                return pytz.timezone(etctz.replace(' ', '_'))

    # systemd distributions use symlinks that include the zone name,
    # see manpage of localtime(5) and timedatectl(1)
    tzpath = os.path.join(_root, 'etc/localtime')
    if os.path.exists(tzpath) and os.path.islink(tzpath):
        tzpath = os.path.realpath(tzpath)
        start = tzpath.find("/")+1
        while start is not 0:
            tzpath = tzpath[start:]
            try:
                return pytz.timezone(tzpath)
            except pytz.UnknownTimeZoneError:
                pass
            start = tzpath.find("/")+1

    # No explicit setting existed. Use localtime
    for filename in ('etc/localtime', 'usr/local/etc/localtime'):
        tzpath = os.path.join(_root, filename)

        if not os.path.exists(tzpath):
            continue
        with open(tzpath, 'rb') as tzfile:
            return pytz.tzfile.build_tzinfo('local', tzfile)

    raise pytz.UnknownTimeZoneError('Can not find any timezone configuration')

def get_localzone():
    """Get the computers configured local timezone, if any."""
    global _cache_tz
    if _cache_tz is None:
        _cache_tz = _get_localzone()
    return _cache_tz

def reload_localzone():
    """Reload the cached localzone. You need to call this if the timezone has changed."""
    global _cache_tz
    _cache_tz = _get_localzone()
    return _cache_tz
