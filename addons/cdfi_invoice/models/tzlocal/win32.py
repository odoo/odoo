try:
    import _winreg as winreg
except ImportError:
    import winreg

from . import windows_tz
import pytz

_cache_tz = None

def valuestodict(key):
    """Convert a registry key's values to a dictionary."""
    dict = {}
    size = winreg.QueryInfoKey(key)[1]
    for i in range(size):
        data = winreg.EnumValue(key, i)
        dict[data[0]] = data[1]
    return dict

def get_localzone_name():
    # Windows is special. It has unique time zone names (in several
    # meanings of the word) available, but unfortunately, they can be
    # translated to the language of the operating system, so we need to
    # do a backwards lookup, by going through all time zones and see which
    # one matches.
    handle = winreg.ConnectRegistry(None, winreg.HKEY_LOCAL_MACHINE)

    TZLOCALKEYNAME = r"SYSTEM\CurrentControlSet\Control\TimeZoneInformation"
    localtz = winreg.OpenKey(handle, TZLOCALKEYNAME)
    keyvalues = valuestodict(localtz)
    localtz.Close()

    if 'TimeZoneKeyName' in keyvalues:
        # Windows 7 (and Vista?)

        # For some reason this returns a string with loads of NUL bytes at
        # least on some systems. I don't know if this is a bug somewhere, I
        # just work around it.
        tzkeyname = keyvalues['TimeZoneKeyName'].split('\x00', 1)[0]
    else:
        # Windows 2000 or XP

        # This is the localized name:
        tzwin = keyvalues['StandardName']

        # Open the list of timezones to look up the real name:
        TZKEYNAME = r"SOFTWARE\Microsoft\Windows NT\CurrentVersion\Time Zones"
        tzkey = winreg.OpenKey(handle, TZKEYNAME)

        # Now, match this value to Time Zone information
        tzkeyname = None
        for i in range(winreg.QueryInfoKey(tzkey)[0]):
            subkey = winreg.EnumKey(tzkey, i)
            sub = winreg.OpenKey(tzkey, subkey)
            data = valuestodict(sub)
            sub.Close()
            try:
                if data['Std'] == tzwin:
                    tzkeyname = subkey
                    break
            except KeyError:
                # This timezone didn't have proper configuration.
                # Ignore it.
                pass

        tzkey.Close()
        handle.Close()

    if tzkeyname is None:
        raise LookupError('Can not find Windows timezone configuration')

    timezone = win_tz.get(tzkeyname)
    if timezone is None:
        # Nope, that didn't work. Try adding "Standard Time",
        # it seems to work a lot of times:
        timezone = win_tz.get(tzkeyname + " Standard Time")

    # Return what we have.
    if timezone is None:
        raise pytz.UnknownTimeZoneError('Can not find timezone ' + tzkeyname)

    return timezone

def get_localzone():
    """Returns the zoneinfo-based tzinfo object that matches the Windows-configured timezone."""
    global _cache_tz
    if _cache_tz is None:
        _cache_tz = pytz.timezone(get_localzone_name())
    return _cache_tz

def reload_localzone():
    """Reload the cached localzone. You need to call this if the timezone has changed."""
    global _cache_tz
    _cache_tz = pytz.timezone(get_localzone_name())
    return _cache_tz
