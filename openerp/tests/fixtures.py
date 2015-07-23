"""
Definition of various "standard" pytest fixtures useful for Odoo test cases
"""

import contextlib
import threading
import itertools

import pytest

from .. import SUPERUSER_ID, api, service
from .. import modules

from . import common

class calling(object):
    def __init__(self, method, obj):
        self.obj = obj
        self.method = getattr(obj, method)
    def __enter__(self):
        return self.obj
    def __exit__(self, *exc_info):
        self.method()

@pytest.yield_fixture(autouse=True)
def current_thread_testing():
    threading.current_thread().testing = True
    yield
    threading.current_thread().testing = False

@pytest.yield_fixture
def registry():
    """ Provides a registry for the globally registered database, clears the
    registry's cache after each test

    .. todo:: look into parameterisation of the db?
    """
    with calling('clear_caches', modules.registry.RegistryManager.get(
            common.get_db_name())) as reg:
        yield reg

@pytest.yield_fixture
def cr(registry):
    """ Provides a test cursor closed after each test function
    """
    with contextlib.closing(registry.cursor()) as cursor:
        yield cursor

@pytest.yield_fixture(scope='module')
def uid():
    yield SUPERUSER_ID

@pytest.yield_fixture
def env(cr, uid):
    """
    Provides a clean environment per test function.

    * Depends on single-function transactions
    * Uses the global superuser (todo: parameterize?)
    """
    with calling('reset', api.Environment(cr, uid, {})) as e:
        yield e

@pytest.yield_fixture(scope='module')
def mod_registry():
    """ Same as ``registry`` but only only clears its cache once per test
    module
    """
    with calling('clear_caches', modules.registry.RegistryManager.get(
            common.get_db_name())) as reg:
        yield reg
@pytest.yield_fixture(scope='module')
def mod_cr(mod_registry):
    """ Same as ``cr``, but the transaction lasts for all of the current
    test module
    """
    with contextlib.closing(mod_registry.cursor()) as cursor:
        yield cursor

@pytest.yield_fixture(scope='module')
def mod_env(mod_cr, uid):
    """ Identical to ``env`` except the environment is scoped to the current
    test module
    """
    with calling('reset', api.Environment(mod_cr, uid, {})) as e:
        yield e

savepoint_seq = itertools.count()
@pytest.yield_fixture
def savepoint(mod_registry, mod_cr, uid):
    """ Runs all tests in current module in the same transaction (via
    ``mod_cr``) but each test runs in its own sub-transaction, with a
    cache-cleared registry and a clean environment.

    Provides the environment as funcarg
    """
    savepoint_id = next(savepoint_seq)
    mod_cr.execute('SAVEPOINT test_%d' % savepoint_id)
    e = api.Environment(mod_cr, uid, {})
    yield e
    e.clear()
    mod_cr.execute('ROLLBACK TO SAVEPOINT test_%d' % savepoint_id)
    mod_registry.clear_caches()

@pytest.yield_fixture(scope='session')
def http():
    """ Ensures a (threaded) HTTP server is running before the test starts.

    The server is provided by the fixture.

    The HTTP server is started once for the first test requiring it and keeps
    running afterwards, it is not restarted for each test.
    """
    # only start the HTTP server if we're not running with one already enabled
    s = service.server.server
    if s:
        yield s
        return

    service.server.load_server_wide_modules()
    s = service.server.server = service.server.ThreadedServer(
        service.wsgi_server.application
    )

    # spawn the HTTP thread but not the cron thread. server.run would
    # block and never execute the test so it's not the right option.
    s.start(stop=True)
    yield s
    s.stop()
