""" Odoo pytest plugin

If this plugin is loaded, only Odoo post-install tests will be discovered, and
only when their containing modules are installed in the provided database.

## Sadness on the stack:

- parametrization is not supported with unittest, and pytest-repeat uses
  parametrization meaning pytest-repeat can't be used to work with (or try and
  suss out) nondeterminism
- pytest-rerunfailures seems to not work at all
- xdist broadly works fine but causes persistent false positive tour failures,
  which generally but don't necessarily disappear when re-running the tours
  (using `--lf`) without xdist
"""
import importlib
import os
import pathlib
import secrets
import shutil
import sys
import threading
import unittest
from collections.abc import Iterator
from contextlib import closing
from os import environ
from pathlib import Path
from shutil import copytree
from types import SimpleNamespace, ModuleType
from typing import Iterable

import _pytest.python
import appdirs
import psycopg2
import py
import pytest

import odoo
from odoo import api
from odoo.modules import module, registry, graph
from odoo.modules.loading import load_module_graph, load_marked_modules
from odoo.service import server
from odoo.sql_db import close_db, db_connect
from odoo.tests import HttpCase, BaseCase

LoadedModules = pytest.StashKey[set[str]]()

SKIP_NON_POST = pytest.mark.skip(reason="non post-install tests are skipped by default")
SKIP_NON_STANDARD = pytest.mark.skip(reason="non-standard tests are skipped by default")
SKIP_INHERITED = pytest.mark.skip(
    reason="inherited tests are skipped unless `allow_inherited_tests_method` "
           "is set on the class also they're bad and should be fixed"
)

pytest_plugins = [
    # pytest does not implement TestCase.subTest by default
    "pytest_subtests",
]

collect_ignore = [
    "__*__",
    # irrelevant frontend stuff
    "static",
    # packaging
    "debian",
    "setup",
]

def pytest_addoption(parser: pytest.Parser) -> None:
    parser.addoption(
        # sadly -d is off-limit
        "--database", "--db",
        help="Database to run tests on. Only tests belonging to modules "
             "installed into the database will be collected.",
    )
    parser.addoption(
        "--addons-path", default="",
        help="Odoo addons path for resolving imports, using PEP 420 namespaces packages is strongly recommended.",
    )
    parser.addoption('--non-standard', action="store_true", help="runs tests which are not marked 'standard', they are skipped by default")
    parser.addoption('--non-post', action="store_true", help="runs tests which are not marked as 'post_install', they are skipped by default")


@pytest.hookimpl(tryfirst=True)
def pytest_configure(config: pytest.Config) -> None:
    if config.getoption("--help"):
        return

    dbname = config.getoption("--database")
    if not dbname:
        raise ValueError("No database specified")

    for ad in config.getoption("--addons-path").split(","):
        ad = os.path.normcase(os.path.abspath(ad.strip()))
        if ad not in odoo.addons.__path__:
            odoo.addons.__path__.append(ad)

    with closing(psycopg2.connect(dbname=dbname)) as conn, conn.cursor() as cr:
        cr.execute("SELECT name FROM ir_module_module WHERE state = 'installed'")
        config.stash[LoadedModules] = {name for [name] in cr}

    # Configuration for Odoo setup
    if not config.getini('python_files'):
        config.addinivalue_line("python_files", "*/tests/test_*.py")


def pytest_ignore_collect(collection_path: pathlib.Path, path: py.path.local, config: pytest.Config) -> bool | None:
    """ Skips collection for modules which are not installed in the current
    database.
    """
    if collection_path.joinpath('__manifest__.py').exists():
        if collection_path.name not in config.stash[LoadedModules]:
            return True


def _get_default_datadir() -> str:
    home = os.path.expanduser('~')
    if os.path.isdir(home):
        func = appdirs.user_data_dir
    else:
        if sys.platform in ['win32', 'darwin']:
            func = appdirs.site_data_dir
        else:
            func = lambda **kwarg: "/var/lib/%s" % kwarg['appname'].lower()
    # copies from release.py
    return func(appname="Odoo", appauthor="OpenERP S.A.")


@pytest.hookimpl(wrapper=True)
def pytest_collection(session: pytest.Session) -> object:
    # needs to be performed before collection in order to import modules in the
    # correct order
    database = session.config.getoption('--database')
    cr = db_connect(database).cursor()
    cr.transaction = api.Transaction(SimpleNamespace(
        _init_modules=set(),
        load=lambda _1, _2: []
    ))

    g = graph.Graph()
    g.add_module(cr, "base", ())
    env = api.Environment(cr, 1, {})
    loaded_modules, processed_modules = load_module_graph(env, g, perform_checks=False)

    previously_processed = -1
    while previously_processed < len(processed_modules):
        previously_processed = len(processed_modules)
        processed_modules += load_marked_modules(
            env, g, ['installed'], (),
            None, None, loaded_modules, False)

    registry.Registry.delete(database)
    close_db(database)

    return (yield)


@pytest.fixture(scope='session')
def odoo_session(pytestconfig: pytest.Config) -> Iterator[registry.Registry]:
    # remove odoo test harness's retry magic, pytest has rerunfailures as well
    # as failure selection (--lf, --sw, ...) and it breaks because pytest
    # doesn't fully implement `unittest.TestResult`
    del BaseCase.run

    # odoo.cli.server.main()
    template = pytestconfig.getoption('--database')

    # alternatively we could request.getfixturevalue('worker_id') but that raises...
    if environ.get('PYTEST_XDIST_WORKER') is not None:
        # if we run multiple test workers against the same db, we get deadlocks
        # and additional failures, so create a copy per worker
        dbname = "testdb_" + secrets.token_urlsafe(16)
        with closing(psycopg2.connect(dbname='postgres')) as conn, conn.cursor() as cr:
            conn.autocommit = True
            cr.execute(f'CREATE DATABASE "{dbname}" TEMPLATE "{template}"')
        dbfilestore = copytree(
            os.path.join(_get_default_datadir(), "filestore", template),
            os.path.join(_get_default_datadir(), "filestore", dbname),
        )
    else:
        dbfilestore = None
        dbname = template

    odoo.tools.config.parse_config(['-d', dbname], setup_logging=False)
    # tell the web client to load the test assets (so tours can run and shit),
    # but prevent running tests via odoo (mostly at_install)
    odoo.tools.config['test_enable'] = True
    odoo.tools.config['test_tags'] = ''
    server.load_server_wide_modules()

    module.current_test = threading.current_thread().testing = True

    # preload registry
    yield registry.Registry.new(dbname)

    threading.current_thread().testing = module.current_test = False

    registry.Registry.delete(dbname)
    close_db(dbname)

    if dbfilestore:
        shutil.rmtree(dbfilestore)
        with closing(psycopg2.connect(dbname='postgres')) as conn, conn.cursor() as cr:
            conn.autocommit = True
            cr.execute(f'DROP DATABASE "{dbname}"')


@pytest.fixture
def odoo_test(odoo_session: registry.Registry, request: pytest.FixtureRequest) -> Iterator[None]:
    module.current_test = request.node.nodeid
    yield
    module.current_test = True


@pytest.fixture(scope='session')
def odoo_http(odoo_session: registry.Registry) -> Iterator[None]:
    """For :class:`HttpCase` tests, we need to start the http server and
    pregenerate the assets.
    """
    server.server = server.ThreadedServer(odoo.http.root)
    # keep the server running until we stop it
    server.server.start(stop=False)
    with odoo_session.cursor() as cr:
        odoo.api.Environment(cr, odoo.SUPERUSER_ID, {})['ir.qweb'] \
            ._pregenerate_assets_bundles()

    yield

    server.server.stop()


def import_path(
    path: str | os.PathLike[str],
    *,
    mode: str,
    root: Path,
    consider_namespace_packages: bool,
) -> ModuleType:
    path = Path(path)
    if not path.exists():
        raise ImportError(path)

    for p in path.parents:
        if str(p) in odoo.addons.__path__:
            prefix = ['odoo', 'addons']
            break
        if str(p) in sys.path:
            prefix = []
            break
    else: # no break
        raise ImportError(f"Can't resolve module for location {path}")

    names = list(path.with_suffix("").relative_to(p).parts)
    if names[-1] == '__init__':
        names.pop()

    modname = '.'.join(prefix + names)
    importlib.import_module(modname)
    return sys.modules[modname]
_pytest.python.import_path = import_path


def pytest_pycollect_makemodule(module_path: pathlib.Path, path: py.path.local, parent: pytest.Item) -> pytest.Module:
    return OdooModule.from_parent(parent, path=module_path)


class OdooModule(pytest.Module):
    def collect(self) -> Iterable[pytest.Item | pytest.Collector]:
        for item in super().collect():
            if isinstance(item, pytest.Class) and issubclass(item.obj, BaseCase):
                item.add_marker(pytest.mark.usefixtures("odoo_test"))
                if issubclass(item.obj, HttpCase):
                    item.add_marker(pytest.mark.usefixtures("odoo_http"))
            yield item



def pytest_collection_modifyitems(config: pytest.Config, items: list[pytest.Item]) -> None:
    """
    - adds the `odoo_test` and `odoo_fixtures` to the relevant classes
    - converts test tags to markers
    - skip any test which is not tagged as standard or post_install unless the
      relevant option is set
    """
    skip_non_standard = None if config.getoption('--non-standard') else SKIP_NON_STANDARD
    skip_non_post = None if config.getoption('--non-post') else SKIP_NON_POST

    for item in items:
        cls = item.parent if isinstance(item.parent, pytest.Class) and issubclass(item.parent.obj, unittest.TestCase) else None
        if cls and item.originalname not in cls.obj.__dict__:
            # if a test method was inherited, skip it unless the class is marked
            # to allow it
            if not getattr(cls.obj, 'allow_inherited_tests_method', False):
                item.add_marker(SKIP_INHERITED)

        ut = cls if cls and hasattr(cls.obj, 'test_tags') else None

        tags = () if ut is None else ut.obj.test_tags

        # marking needs to be done on the item to avoid inheritance issues
        # mucking things up, as markers are additive through inheritance
        #
        # also we want to skip free functions (e.g. standalone) and non-odoo test cases
        if skip_non_standard and 'standard' not in tags:
            item.add_marker(skip_non_standard)
        if skip_non_post and 'post_install' not in tags:
            item.add_marker(skip_non_post)
        for tag in tags:
            item.add_marker(tag)
