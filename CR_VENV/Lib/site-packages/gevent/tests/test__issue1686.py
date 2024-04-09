# -*- coding: utf-8 -*-
"""
Tests for https://github.com/gevent/gevent/issues/1686
which is about destroying a hub when there are active
callbacks or IO in operation.
"""
from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

import os
import unittest

from gevent import testing as greentest

# Don't let the testrunner put us in a process with other
# tests; we are strict on the state of the hub and greenlets.
# pragma: testrunner-no-combine

@greentest.skipOnWindows("Uses os.fork")
class TestDestroyInChildWithActiveSpawn(unittest.TestCase):

    def test(self): # pylint:disable=too-many-locals
        # If this test is broken, there are a few failure modes.
        # - In the original examples, the parent process just hangs, because the
        #   child has raced ahead, spawned the greenlet and read the data. When the
        #   greenlet goes to read in the parent, it blocks, and the hub and loop
        #   wait for it.
        # - Here, our child detects the greenlet ran when it shouldn't and
        #   raises an error, which translates to a non-zero exit status,
        #   which the parent checks for and fails by raising an exception before
        #   returning control to the hub. We can replicate the hang by removing the
        #   assertion in the child.
        from time import sleep as hang

        from gevent import get_hub
        from gevent import spawn
        from gevent.socket import wait_read
        from gevent.os import nb_read
        from gevent.os import nb_write
        from gevent.os import make_nonblocking
        from gevent.os import fork
        from gevent.os import waitpid

        pipe_read_fd, pipe_write_fd = os.pipe()
        make_nonblocking(pipe_read_fd)
        make_nonblocking(pipe_write_fd)

        run = []

        def reader():
            run.append(1)
            return nb_read(pipe_read_fd, 4096)

        # Put data in the pipe
        DATA = b'test'
        nb_write(pipe_write_fd, DATA)
        # Make sure we're ready to read it
        wait_read(pipe_read_fd)

        # Schedule a greenlet to start
        reader = spawn(reader)

        hub = get_hub()
        pid = fork()
        if pid == 0:
            # Child destroys the hub. The reader should not have run.
            hub.destroy(destroy_loop=True)
            self.assertFalse(run)
            os._exit(0)
            return

        # The parent.
        # Briefly prevent us from spinning our event loop.
        hang(0.5)
        wait_child_result = waitpid(pid, 0)
        self.assertEqual(wait_child_result, (pid, 0))
        # We should get the data; the greenlet only runs in the parent.
        data = reader.get()
        self.assertEqual(run, [1])
        self.assertEqual(data, DATA)


if __name__ == '__main__':
    greentest.main()
