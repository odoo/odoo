from __future__ import annotations

import typing

from odoo.libs.debug_log import DebugLog
from odoo.orm.model_test_env import (
    load_module_data,
    model_test_env,
    module_model_classes,
)

from .transaction_case import BaseCase

_debug = DebugLog(__name__)

# what the loader creates before any data file: module rows and their
# categories come from Module.update_list(), which reads the manifests
LOADER_OWNED_DATA = ("data/ir_module_module.xml",)


class InMemoryCase(BaseCase):
    # the point of the class is to run another class's methods, which the
    # loader collects only for a class that says so
    allow_inherited_tests_method = True

    hosts_modules: typing.ClassVar[tuple[str, ...]] = ("base",)
    skip_data_files: typing.ClassVar[tuple[str, ...]] = LOADER_OWNED_DATA

    _env_context: typing.ClassVar[typing.Any] = None

    @classmethod
    def setUpClass(cls) -> None:
        super().setUpClass()
        classes: list[typing.Any] = []
        for module in cls.hosts_modules:
            classes.extend(module_model_classes(module))
        # the same environment the DB-free unit tests build, held open for
        # the class: its fixtures mirror base_data.sql, it reflects ir.model
        # and it declares the table-inheritance trees
        cls._env_context = model_test_env(*classes, check_cache=False)
        cls.env = cls._env_context.__enter__()
        cls.addClassCleanup(cls._close_env_context)
        cls.cr = typing.cast("typing.Any", cls.env.cr)
        cls.registry = typing.cast("typing.Any", cls.env.registry)
        for module in cls.hosts_modules:
            load_module_data(cls.env, module, skip=cls.skip_data_files)
        cls.env.flush_all()
        cls.env.invalidate_all()
        _debug.lifecycle(
            "test.in_memory.class_hosted",
            cls=cls.__qualname__,
            modules=len(cls.hosts_modules),
            models=len(cls.registry.models),
        )

    @classmethod
    def _close_env_context(cls) -> None:
        context, cls._env_context = cls._env_context, None
        if context is not None:
            context.__exit__(None, None, None)

    def setUp(self) -> None:
        # the per-test rollback, which a class hosting another one gets from
        # TransactionCase's own setUp below and a class inheriting only this
        # one would not get at all; nesting the two is harmless, the outer
        # snapshot being the one restored last
        self.env.flush_all()
        savepoint = self.env.cr.savepoint(flush=False)
        # the ormcache is not storage and the snapshot does not hold it: a
        # value the test read back is still cached after the rollback
        self.addCleanup(self.registry.clear_all_caches)
        self.addCleanup(self.env.transaction.clear)
        self.addCleanup(savepoint.close)
        super().setUp()
