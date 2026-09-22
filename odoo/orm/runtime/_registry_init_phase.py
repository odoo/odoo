from collections.abc import Callable, Iterable, Iterator
from contextlib import contextmanager
from functools import partial
from typing import Any

from odoo.libs.debug_log import DebugLog

from ._init_phase import InitModelsPhase
from ._registry_stubs import _RegistryStubs

_debug = DebugLog(__name__)


class _RegistryInitPhaseMixin(_RegistryStubs):
    __slots__ = ()

    _init_phase: InitModelsPhase | None

    def _init_phase_state(self) -> None:
        self._init_phase = None

    @property
    def init_phase(self) -> InitModelsPhase:
        if self._init_phase is None:
            raise RuntimeError(
                "Registry.init_phase is only available while init_models() is "
                "running: it holds state for one module-initialisation pass "
                "(the post-init queue, the foreign keys to reconcile, the "
                "many2many relations to reflect). A caller reaching it outside "
                "that window -- typically a field's update_db() run at some "
                "other time -- is the bug."
            )
        return self._init_phase

    @contextmanager
    def init_models_window(
        self, install: bool, *, model_tables: Iterable[str] = ()
    ) -> Iterator[InitModelsPhase]:
        if self._init_phase is not None:
            raise RuntimeError(
                "Registry.init_models_window() cannot be nested: one "
                "module-initialisation pass is already open"
            )
        self._init_phase = InitModelsPhase(
            install=install,
            model_tables=frozenset(model_tables),
        )
        _debug.lifecycle("registry.init_phase.opened", install=install)
        try:
            yield self._init_phase
            self.drain_post_init()
        finally:
            _debug.lifecycle(
                "registry.init_phase.closed",
                relations=len(self._init_phase.relation_reflections),
            )
            self._init_phase = None

    def drain_post_init(self) -> None:
        post_init_queue = self.init_phase.post_init_queue
        _debug.pipeline("registry.init_phase.drain", queued=len(post_init_queue))
        while post_init_queue:
            post_init_queue.popleft()()

    def post_init(self, func: Callable, *args: Any, **kwargs: Any) -> None:
        self.init_phase.post_init_queue.append(partial(func, *args, **kwargs))

    def register_relation_table(
        self,
        model_name: str,
        relation: str,
        module: str | None,
        *,
        reflect: bool = True,
    ) -> bool:
        """Admit field-owned tables; payload models retain their own schema lifecycle.

        All models are assembled before this phase begins, even when their tables
        have not been created yet. Manual relations need the same ownership check
        but do not acquire module-uninstall metadata.
        """
        phase = self.init_phase
        if relation in phase.model_tables:
            _debug.logic(
                "registry.relation_table.owned_by_model",
                model=model_name,
                relation=relation,
            )
            return False
        if reflect:
            phase.relation_reflections.add((model_name, relation, module))
        return True
