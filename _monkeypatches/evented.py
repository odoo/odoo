"""
Running mode flags (gevent, prefork)

This should be imported as early as possible.
It will initialize the `odoo.evented` variable.
"""
import odoo
import sys

odoo.evented = False


def patch_evented():
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
