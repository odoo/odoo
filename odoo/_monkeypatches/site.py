"""Patcher for any change not strictly related to an stdlib module

"""

import codecs
import encodings.aliases
import re
import sys

import babel.core

import odoo


def patch_module():
    patch_evented()
    patch_codecs()


odoo.evented = False


def patch_evented():
    """Running mode flags (gevent, prefork)

    This should be executed early. It will initialize the `odoo.evented` variable.
    """
    if odoo.evented or not (len(sys.argv) > 1 and sys.argv[1] == 'gevent'):
        return
    sys.argv.remove('gevent')
    import gevent.monkey  # noqa: PLC0415
    import psycopg2  # noqa: PLC0415
    from gevent.socket import wait_read, wait_write  # noqa: PLC0415
    gevent.monkey.patch_all()

    def gevent_wait_callback(conn, timeout=None):
        """A wait callback useful to allow gevent to work with Psycopg."""
        # Copyright (C) 2010-2012 Daniele Varrazzo <daniele.varrazzo@gmail.com>
        # This function is borrowed from psycogreen module which is licensed
        # under the BSD license (see in odoo/debian/copyright)
        while 1:
            state = conn.poll()
            if state == psycopg2.extensions.POLL_OK:
                break
            elif state == psycopg2.extensions.POLL_READ:
                wait_read(conn.fileno(), timeout=timeout)
            elif state == psycopg2.extensions.POLL_WRITE:
                wait_write(conn.fileno(), timeout=timeout)
            else:
                raise psycopg2.OperationalError(
                    "Bad result from poll: %r" % state)

    psycopg2.extensions.set_wait_callback(gevent_wait_callback)
    odoo.evented = True


def patch_codecs():
    # ---------------------------------------------------------
    # some charset are known by Python under a different name
    # ---------------------------------------------------------

    encodings.aliases.aliases['874'] = 'cp874'
    encodings.aliases.aliases['windows_874'] = 'cp874'

    # ---------------------------------------------------------
    # alias hebrew iso-8859-8-i and iso-8859-8-e on iso-8859-8
    # https://bugs.python.org/issue18624
    # ---------------------------------------------------------

    iso8859_8 = codecs.lookup('iso8859_8')
    iso8859_8ie_re = re.compile(r'iso[-_]?8859[-_]8[-_]?[ei]', re.IGNORECASE)
    codecs.register(lambda charset: iso8859_8 if iso8859_8ie_re.match(charset) else None)

    # To remove when corrected in Babel
    babel.core.LOCALE_ALIASES['nb'] = 'nb_NO'
