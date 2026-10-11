# Part of Odoo. See LICENSE file for full copyright and licensing details.


def format_seconds(env, seconds):
    """ Format a number of seconds the way a duration is displayed to the user,
    e.g. "1h 23m 45s". """
    if not seconds:
        return env._("0s")
    if seconds < 60:
        return env._("%(seconds)ss", seconds=seconds)
    minutes, seconds = divmod(seconds, 60)
    if minutes < 60:
        return env._("%(minutes)sm %(seconds)ss", minutes=minutes, seconds=seconds)
    hours, minutes = divmod(minutes, 60)
    return env._("%(hours)sh %(minutes)sm %(seconds)ss", hours=hours, minutes=minutes, seconds=seconds)
