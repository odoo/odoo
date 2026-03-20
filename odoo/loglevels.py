# Part of Odoo. See LICENSE file for full copyright and licensing details.
LOG_NOTSET = 'notset'
LOG_DEBUG = 'debug'
LOG_INFO = 'info'
LOG_WARNING = 'warn'
LOG_ERROR = 'error'
LOG_CRITICAL = 'critical'


def exception_to_unicode(e):
    if getattr(e, 'args', ()):
        return "\n".join(map(str, e.args))
    try:
        return str(e)
    except Exception:
        return "Unknown message"
