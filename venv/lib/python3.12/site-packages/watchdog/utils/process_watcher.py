from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from watchdog.utils import BaseThread

if TYPE_CHECKING:
    import subprocess
    from typing import Callable

logger = logging.getLogger(__name__)


class ProcessWatcher(BaseThread):
    def __init__(self, popen_obj: subprocess.Popen, process_termination_callback: Callable[[], None] | None) -> None:
        super().__init__()
        self.popen_obj = popen_obj
        self.process_termination_callback = process_termination_callback

    def run(self) -> None:
        while self.popen_obj.poll() is None:
            if self.stopped_event.wait(timeout=0.1):
                return

        try:
            if not self.stopped_event.is_set() and self.process_termination_callback:
                self.process_termination_callback()
        except Exception:
            logger.exception("Error calling process termination callback")
