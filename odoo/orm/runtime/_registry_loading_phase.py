from collections.abc import Iterable, Iterator
from contextlib import contextmanager

from odoo.libs.debug_log import DebugLog

from ._loading_phase import LoadingPhase
from ._registry_stubs import _RegistryStubs

_debug = DebugLog(__name__)


class _RegistryLoadingPhaseMixin(_RegistryStubs):
    __slots__ = ()

    _loading: LoadingPhase | None

    def _loading_phase_state(self) -> None:
        self._loading = None

    @property
    def is_loading(self) -> bool:
        return self._loading is not None

    @property
    def loading(self) -> LoadingPhase:
        if self._loading is None:
            raise RuntimeError(
                "Registry.loading is only available while load_modules() is "
                "running: it holds the module loader's state for one load "
                "(the modules to re-initialise, the xmlids written so far, "
                "whether the configured languages were loaded). A caller "
                "reaching it once the registry is ready is the bug."
            )
        return self._loading

    @contextmanager
    def loading_window(self) -> Iterator[LoadingPhase]:
        if self._loading is not None:
            raise RuntimeError(
                "Registry.loading_window() cannot be nested: one module load "
                "is already open"
            )
        self._loading = LoadingPhase()
        _debug.lifecycle("registry.loading.opened", db=self.db_name)
        try:
            yield self._loading
        finally:
            _debug.lifecycle(
                "registry.loading.closed",
                db=self.db_name,
                reinit=len(self._loading.reinit_modules),
                xmlids=len(self._loading.xmlids_written),
            )
            self._loading = None

    def record_xmlids_written(self, xml_ids: Iterable[str]) -> None:
        phase = self._loading
        if phase is not None and phase.xmlid_recorder is not None:
            phase.xmlid_recorder.update(xml_ids)
