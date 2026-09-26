# Part of Odoo. See LICENSE file for full copyright and licensing details.
import logging
import resource
import threading

from odoo.tests import BaseCase, tagged

_logger = logging.getLogger(__name__)

MiB = 1024 * 1024


def _vmsize():
    with open('/proc/self/status', encoding='ascii') as status:
        line = next(line for line in status if line.startswith('VmSize:'))
    return int(line.split()[1]) * 1024


def _start_threads(count):
    stop = threading.Event()
    threads = []
    try:
        for _i in range(count):
            thread = threading.Thread(target=stop.wait, daemon=True)
            thread.start()
            threads.append(thread)
    finally:
        stop.set()
        for thread in threads:
            thread.join()


@tagged('post_install', '-at_install')
class TestRlimitAs(BaseCase):

    def test_import_keeps_room_for_threads(self):
        """limit_memory_hard is enforced as RLIMIT_AS, which counts reserved
        address space, not resident memory. A dependency that reserves a large
        region on import must not take away the room the server needs to start
        its request threads."""
        soft, _hard = resource.getrlimit(resource.RLIMIT_AS)
        if soft == resource.RLIM_INFINITY:
            self.skipTest("RLIMIT_AS is not set (limit_memory_hard disabled or not Linux)")

        before = _vmsize()
        _start_threads(1)
        thread_cost = max(_vmsize() - before, 8 * MiB)
        count = int((soft - _vmsize()) * 0.6 // thread_cost)
        _start_threads(count)

        vm_before_import = _vmsize()
        import device_detector  # noqa: F401, PLC0415
        vm_after_import = _vmsize()
        _logger.info(
            "RLIMIT_AS %d MiB, VmSize %d MiB -> %d MiB after importing device_detector, "
            "starting %d threads of ~%d MiB each again",
            soft // MiB, vm_before_import // MiB, vm_after_import // MiB, count, thread_cost // MiB,
        )
        _start_threads(count)
