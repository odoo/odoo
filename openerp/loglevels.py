# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2004-2009 Tiny SPRL (<http://tiny.be>).
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################

import sys
import logging

LOG_NOTSET = 'notset'
LOG_DEBUG = 'debug'
LOG_TEST = 'test'
LOG_INFO = 'info'
LOG_WARNING = 'warn'
LOG_ERROR = 'error'
LOG_CRITICAL = 'critical'

logging.TEST = logging.INFO - 5
logging.addLevelName(logging.TEST, 'TEST')

_logger = logging.getLogger(__name__)

class Logger(object):
    def __init__(self):
        _logger.warning(
            "The netsvc.Logger API shouldn't be used anymore, please "
            "use the standard `logging.getLogger` API instead.")
        super(Logger, self).__init__()

    def notifyChannel(self, name, level, msg):
        _logger.warning(
            "notifyChannel API shouldn't be used anymore, please use "
            "the standard `logging` module instead.")
        from service.web_services import common

        log = logging.getLogger(__name__ + '.deprecated.' + ustr(name))

        if level in [LOG_TEST] and not hasattr(log, level):
            fct = lambda msg, *args, **kwargs: log.log(getattr(logging, level.upper()), msg, *args, **kwargs)
            setattr(log, level, fct)


        level_method = getattr(log, level)

        if isinstance(msg, Exception):
            msg = exception_to_unicode(msg)

        try:
            msg = ustr(msg).strip()
            if level in (LOG_ERROR, LOG_CRITICAL): # and tools.config.get_misc('debug','env_info',False):
                msg = common().exp_get_server_environment() + "\n" + msg

            result = msg.split('\n')
        except UnicodeDecodeError:
            result = msg.strip().split('\n')
        try:
            if len(result)>1:
                for idx, s in enumerate(result):
                    level_method('[%02d]: %s' % (idx+1, s,))
            elif result:
                level_method(result[0])
        except IOError:
            # TODO: perhaps reset the logger streams?
            #if logrotate closes our files, we end up here..
            pass
        except Exception:
            # better ignore the exception and carry on..
            pass

    def set_loglevel(self, level, logger=None):
        if logger is not None:
            log = logging.getLogger(str(logger))
        else:
            log = logging.getLogger()
        log.setLevel(logging.INFO) # make sure next msg is printed
        log.info("Log level changed to %s" % logging.getLevelName(level))
        log.setLevel(level)

    def shutdown(self):
        logging.shutdown()

# TODO get_encodings, ustr and exception_to_unicode were originally from tools.misc.
# There are here until we refactor tools so that this module doesn't depends on tools.

def get_encodings(hint_encoding='utf-8'):
    fallbacks = {
        'latin1': 'latin9',
        'iso-8859-1': 'iso8859-15',
        'cp1252': '1252',
    }
    if hint_encoding:
        yield hint_encoding
        if hint_encoding.lower() in fallbacks:
            yield fallbacks[hint_encoding.lower()]

    # some defaults (also taking care of pure ASCII)
    for charset in ['utf8','latin1']:
        if not (hint_encoding) or (charset.lower() != hint_encoding.lower()):
            yield charset

    from locale import getpreferredencoding
    prefenc = getpreferredencoding()
    if prefenc and prefenc.lower() != 'utf-8':
        yield prefenc
        prefenc = fallbacks.get(prefenc.lower())
        if prefenc:
            yield prefenc

def ustr(value, hint_encoding='utf-8', errors='strict'):
    """This method is similar to the builtin `str` method, except
       it will return unicode() string.

    :param value: the value to convert
    :param hint_encoding: an optional encoding that was detected
                          upstream and should be tried first to
                          decode ``value``.
    :param errors: specifies the treatment of characters which are
        invalid in the input encoding (see ``unicode()`` constructor)

    :rtype: unicode
    :return: unicode string
    """
    if isinstance(value, Exception):
        return exception_to_unicode(value)

    if isinstance(value, unicode):
        return value

    if not isinstance(value, basestring):
        try:
            return unicode(value)
        except Exception:
            raise UnicodeError('unable to convert %r' % (value,))

    for ln in get_encodings(hint_encoding):
        try:
            return unicode(value, ln, errors=errors)
        except Exception:
            pass
    raise UnicodeError('unable to convert %r' % (value,))


def exception_to_unicode(e):
    if (sys.version_info[:2] < (2,6)) and hasattr(e, 'message'):
        return ustr(e.message)
    if hasattr(e, 'args'):
        return "\n".join((ustr(a) for a in e.args))
    try:
        return unicode(e)
    except Exception:
        return u"Unknown message"

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
