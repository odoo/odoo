# Make sure that libev child watchers, implicitly installed through the use
# of subprocess, do not cause waitpid() to fail to poll for processes.
# NOTE: This was only reproducible under python 2.
from __future__ import print_function
import gevent
from gevent import monkey
monkey.patch_all()

import sys
from multiprocessing import Process
from subprocess import Popen, PIPE

from gevent import testing as greentest

def f(sleep_sec):
    gevent.sleep(sleep_sec)



class TestIssue600(greentest.TestCase):

    __timeout__ = greentest.LARGE_TIMEOUT

    @greentest.skipOnLibuvOnPyPyOnWin("hangs")
    def test_invoke(self):
        # Run a subprocess through Popen to make sure
        # libev is handling SIGCHLD. This could *probably* be simplified to use
        # just hub.loop.install_sigchld
        # (no __enter__/__exit__ on Py2) pylint:disable=consider-using-with
        p = Popen([sys.executable, '-V'], stdout=PIPE, stderr=PIPE)
        gevent.sleep(0)
        p.communicate()
        gevent.sleep(0)

    def test_process(self):
        # Launch
        p = Process(target=f, args=(0.5,))
        p.start()

        with gevent.Timeout(3):
            # Poll for up to 10 seconds. If the bug exists,
            # this will timeout because our subprocess should
            # be long gone by now
            p.join(10)


if __name__ == '__main__':
    greentest.main()
