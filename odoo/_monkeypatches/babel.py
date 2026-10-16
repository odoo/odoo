from babel import dates


# Copy of get_timezone_gmt as fixed by https://github.com/python-babel/babel/pull/1291
def get_timezone_gmt(datetime=None, width='long', locale=None, return_z=False):
    datetime = dates._ensure_datetime_tzinfo(dates._get_datetime(datetime))
    locale = dates.Locale.parse(locale or dates.LC_TIME)

    offset = datetime.tzinfo.utcoffset(datetime)
    seconds = offset.days * 24 * 60 * 60 + offset.seconds
    if return_z and seconds == 0:
        return 'Z'
    sign = '-' if seconds < 0 else '+'
    hours, seconds = divmod(abs(seconds), 3600)
    if seconds == 0 and width == 'iso8601_short':
        return '%s%02d' % (sign, hours)
    elif width == 'short' or width == 'iso8601_short':  # noqa: RET505
        pattern = '%s%02d%02d'
    elif width == 'iso8601':
        pattern = '%s%02d:%02d'
    else:
        pattern = locale.zone_formats['gmt'] % '%s%02d:%02d'
    return pattern % (sign, hours, seconds // 60)


def patch_module():
    # Babel floors the hours of negative offsets that are not whole hours, so
    # for example America/St_Johns (UTC-03:30) is rendered "GMT-04:30".
    # Every offset in a date pattern goes through get_timezone_gmt
    # (Z, O, x, X, and z when the zone has no localized name). Fixed after Babel 2.18.0.
    dates.get_timezone_gmt = get_timezone_gmt
