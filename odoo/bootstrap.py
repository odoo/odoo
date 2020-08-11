# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.


def setup(argv=None):
    """
    TODO Document me
    explain why the argv is nice to integrate with external stuffs
    """

    # only setup once
    if getattr(setup, "called", False):
        return
    setup.called = True

    _ensure_version()

    # phase 1, static library configuration
    _force_utc()
    _fix_pypdf2()
    _enable_warnings()

    # phase 2, configuration loading and exposure
    from . import config as config_module
    config_module.setup(argv)

    # phase 3, dynamic library configuration
    if config_module.config.evented:
        _use_cooperative_networking()

    # phase 4, import all odoo libraries and setup dynamic namespaces
    _setup_import_system()

    # phase 5, place some deprecated aliases
    _place_backward_compatible_aids()


def _setup_import_system():
    import importlib
    import odoo

    #----------------------------------------------------------
    # Configuration
    #----------------------------------------------------------
    import odoo.config as config_mod
    odoo.config = config_mod.config

    #----------------------------------------------------------
    # Namespaces
    #----------------------------------------------------------
    import odoo.addons
    import odoo.upgrade
    import odoo.modules
    odoo.modules.initialize_sys_path()

    #----------------------------------------------------------
    # Standalone Imports
    #----------------------------------------------------------
    import odoo.conf
    import odoo.exceptions
    import odoo.loglevels
    import odoo.logging_config
    import odoo.osv
    import odoo.release
    import odoo.service
    import odoo.sql_db
    import odoo.tools

    #----------------------------------------------------------
    # Model classes, fields, api decorators, and translations
    #----------------------------------------------------------
    import odoo.models
    import odoo.fields
    import odoo.api
    from odoo.tools.translate import _, _lt
    odoo._ = _
    odoo._lt = _lt

    #----------------------------------------------------------
    # Other imports, which may require stuff from above
    #----------------------------------------------------------
    import odoo.cli
    import odoo.http


def _ensure_version():
    """ Ensure a minimal viable python interpreter is used. """
    import sys
    if sys.version_info < (3, 7):
        raise OSError("Outdated python version detected %s.%s, Odoo requires Python >= 3.7 to run." % sys.version_info[:2])


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
        'babel.localedata',# babel importing ABC from collections
        'werkzeug.datastructures',#werkzeug importing ABC from collections
    ]:
        warnings.filterwarnings('ignore', category=DeprecationWarning, module=module)


def _force_utc():
    """ libc UTC hack, make sure everything runs in UTC. """
    import os, time
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

        def _decompress(data):
            zobj = zlib.decompressobj()
            return zobj.decompress(data)

        PyPDF2.filters.decompress = _decompress
    except ImportError:
        pass # no fix required


def _use_cooperative_networking():
    """
    Patch socket, threading and signal libraries to automatically enable
    NO_WAIT like options. This prevent recv/send like calls to block the
    entire thread thus allow multi concurrent transmitions and code
    execution. Thanks to gevent, the user-code can continue to use those
    library like if they were still blocking so no further modification
    is required. Used by the longpolling dedicated process when the Odoo
    server is ran in multi-worker mode.
    """
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

def _place_backward_compatible_aids():
    import odoo
    import warnings

    moved_tmpl = "{} has been moved to {}. Please use the later."
    def warn_moved(from_, to):
        warnings.warn(
            moved_tmpl.format(from_, to),
            DeprecationWarning,
            stacklevel=5,  # warn_moved > evented > lazy > lazy > real src
        )


    @odoo.tools.lazy
    def evented():
        warn_moved('odoo.evented', 'odoo.config.evented')
        return odoo.config.evented

    @odoo.tools.lazy
    def multi_process():
        warn_moved('odoo.multi_process', 'odoo.config.multi_process')
        return odoo.config.multi_process

    @odoo.tools.lazy
    def addons_paths():
        warn_moved('odoo.conf.addons_path', "odoo.config['addons_paths']")
        return odoo.config['addons_paths']

    @odoo.tools.lazy
    def server_wide_modules():
        warn_moved('odoo.conf.server_wide_modules', "odoo.config['server_wide_modules']")
        return odoo.config['server_wide_modules']

    odoo.evented = evented
    odoo.multi_process = multi_process
    odoo.conf.addons_paths = addons_paths
    odoo.conf.server_wide_modules = server_wide_modules
