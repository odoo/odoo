# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

def boot():
    # only boot once
    if getattr(boot, "called", False):
        return
    boot.called = True

    _ensure_version()

    # phase 1, static library configuration
    _force_utc()
    _fix_pypdf2()
    _enable_warnings()

    # phase 2, configuration loading and exposure
    from . import conf
    conf.load()
    conf.expose()

    # phase 3, dynamic library configuration
    if conf.subcommand == 'gevent':
        _use_cooperative_networking()
    _configure_logging()

    # phase 4, addons_path and upgrade_path namespaces setup
    from . import addons, upgrade
    from . import modules
    modules.initialize_sys_path()


def _ensure_version():
    """ Ensure a minimal viable python interpreter is used. """
    import sys
    if sys.version_info < (3, 6):
        raise OSError("Outdated python version detected, Odoo requires Python >= 3.6 to run.")


def _enable_warnings():
    """
    Enable the python standard warnings (equivalent of running python
    with the ``-W default`` command line option) with some tuning
    """
    import warnings
    warnings.filterwarnings('default', category=DeprecationWarning)

    # ignore deprecation warnings from invalid escape (there's a ton and it's
    # pretty likely a super low-value signal)
    warnings.filterwarnings('ignore', r'^invalid escape sequence \\.', category=DeprecationWarning)
    # ignore a bunch of warnings we can't really fix ourselves
    for module in [
        'setuptools.depends',# older setuptools version using imp
        'zeep.loader',# zeep using defusedxml.lxml
        'reportlab.lib.rl_safe_eval',# reportlab importing ABC from collections
        'xlrd/xlsx',# xlrd mischecks iter() on trees or something so calls deprecated getiterator() instead of iter()
    ]:
        warnings.filterwarnings('ignore', category=DeprecationWarning, module=module)


def _force_utc():
    """ libc UTC hack, make sure everything runs in UTC. """
    import os
    os.environ['TZ'] = 'UTC' # Set the timezone
    if hasattr(time, 'tzset'):
        time.tzset()


def _fix_pypdf2():
    """
    Ensure that zlib does not throw error -5 when decompressing
    because some pdf won't fit into allocated memory
    import time
    """
    import PyPDF2
    try:
        import zlib

        def __decompress(data):
            zobj = zlib.decompressobj()
            return zobj.decompress(data)

        PyPDF2.filters.decompress = _decompress
    except ImportError:
        pass # no fix required


def _use_cooperative_networking():
    import gevent.monkey
    import psycopg2
    from gevent.socket import wait_read, wait_write
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


def _configure_logging():
    from . import netsvc
    netsvc.init_logger()
