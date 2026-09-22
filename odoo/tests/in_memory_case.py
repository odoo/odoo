from __future__ import annotations

import atexit
import typing

from odoo.libs.debug_log import DebugLog
from odoo.orm.model_test_env import (
    load_module_data,
    model_test_env,
    module_model_classes,
)

from .transaction_case import TransactionCase

_debug = DebugLog(__name__)

# what the loader creates before any data file: module rows and their
# categories come from Module.update_list(), which reads the manifests
LOADER_OWNED_DATA = ("data/ir_module_module.xml",)

# building the environment is the whole cost of hosting a class -- some 30 s
# for `base`, most of it the currency and country files -- and it is the same
# environment for every class naming the same modules, so the process builds
# one per module set and each class takes a savepoint over it
_HOSTS: dict[tuple[str, ...], typing.Any] = {}


def _close_hosts() -> None:
    while _HOSTS:
        modules, context = _HOSTS.popitem()
        _ENVS.pop(modules, None)
        context.__exit__(None, None, None)


atexit.register(_close_hosts)


_ENVS: dict[tuple[str, ...], typing.Any] = {}


def _host_environment(modules: tuple[str, ...]) -> typing.Any:
    env = _ENVS.get(modules)
    if env is None:
        classes: list[typing.Any] = []
        for module in modules:
            classes.extend(module_model_classes(module))
        context = model_test_env(*classes, check_cache=False)
        env = context.__enter__()
        for module in modules:
            load_module_data(env, module, skip=InMemoryCase.skip_data_files)
        env.flush_all()
        env.invalidate_all()
        _HOSTS[modules] = context
        _ENVS[modules] = env
        _debug.lifecycle(
            "test.in_memory.host_built",
            modules=len(modules),
            models=len(env.registry.models),
        )
    return env


class InMemoryCase(TransactionCase):
    # the point of the class is to run another class's methods, which the
    # loader collects only for a class that says so
    allow_inherited_tests_method = True

    hosts_modules: typing.ClassVar[tuple[str, ...]] = ("base",)
    skip_data_files: typing.ClassVar[tuple[str, ...]] = LOADER_OWNED_DATA

    @classmethod
    def _open_class_transaction(cls) -> None:
        # everything a TransactionCase does around the transaction -- the
        # per-test savepoint, the cache clears, the callback restore -- is
        # inherited; only what opens it differs, and a hosted class's own
        # setUpClass therefore builds its fixtures here rather than in the
        # database the run is otherwise using
        cls.env = typing.cast("typing.Any", _host_environment(cls.hosts_modules))
        cls.cr = typing.cast("typing.Any", cls.env.cr)
        cls.registry = typing.cast("typing.Any", cls.env.registry)
        cls.env.transaction.default_env = cls.env
        # the class's own snapshot over the shared environment, so what its
        # setUpClass creates is gone before the next class takes one
        cls.env.flush_all()
        savepoint = cls.cr.savepoint(flush=False)
        cls.addClassCleanup(savepoint.close)
        cls.addClassCleanup(cls.env.transaction.clear)
        cls.addClassCleanup(cls.registry.clear_all_caches)
        _debug.lifecycle(
            "test.in_memory.class_hosted",
            cls=cls.__qualname__,
            modules=len(cls.hosts_modules),
            models=len(cls.registry.models),
        )
