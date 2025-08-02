from __future__ import print_function
from gevent import monkey
monkey.patch_all()

import os
import unittest
import multiprocessing

import gevent

hub = gevent.get_hub()
pid = os.getpid()
newpid = None


def on_fork():
    global newpid
    newpid = os.getpid()

fork_watcher = hub.loop.fork(ref=False)
fork_watcher.start(on_fork)


def in_child(q):
    # libev only calls fork callbacks at the beginning of
    # the loop; we use callbacks extensively so it takes *two*
    # calls to sleep (with a timer) to actually get wrapped
    # around to the beginning of the loop.
    gevent.sleep(0.001)
    gevent.sleep(0.001)
    q.put(newpid)


class Test(unittest.TestCase):

    def test(self):
        self.assertEqual(hub.threadpool.size, 0)
        # Use a thread to make us multi-threaded
        hub.threadpool.apply(lambda: None)
        self.assertEqual(hub.threadpool.size, 1)

        # Not all platforms use fork by default, so we want to force it,
        # where possible. The test is still useful even if we can't
        # fork though.
        try:
            fork_ctx = multiprocessing.get_context('fork')
        except (AttributeError, ValueError):
            # ValueError if fork isn't supported.
            # AttributeError on Python 2, which doesn't have get_context
            fork_ctx = multiprocessing

        # If the Queue is global, q.get() hangs on Windows; must pass as
        # an argument.
        q = fork_ctx.Queue()
        p = fork_ctx.Process(target=in_child, args=(q,))
        p.start()
        p.join()
        p_val = q.get()

        self.assertIsNone(
            newpid,
            "The fork watcher ran in the parent for some reason."
        )
        self.assertIsNotNone(
            p_val,
            "The child process returned nothing, meaning the fork watcher didn't run in the child."
        )
        self.assertNotEqual(p_val, pid)
        assert p_val != pid

if __name__ == '__main__':
    # Must call for Windows to fork properly; the fork can't be in the top-level
    multiprocessing.freeze_support()

    # fork watchers weren't firing in multi-threading processes.
    # This test is designed to prove that they are.
    # However, it fails on Windows: The fork watcher never runs!
    # This makes perfect sense: on Windows, our patches to os.fork()
    # that call gevent.hub.reinit() don't get used; os.fork doesn't
    # exist and multiprocessing.Process uses the windows-specific _subprocess.CreateProcess()
    # to create a whole new process that has no relation to the current process;
    # that process then calls multiprocessing.forking.main() to do its work.
    # Since no state is shared, a fork watcher cannot exist in that process.
    unittest.main()
