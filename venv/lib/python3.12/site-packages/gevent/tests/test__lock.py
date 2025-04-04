from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

from gevent import lock


import gevent.testing as greentest
from gevent.tests import test__semaphore


class TestRLockMultiThread(test__semaphore.TestSemaphoreMultiThread):

    def _makeOne(self):
        # If we don't set the hub before returning,
        # there's a potential race condition, if the implementation
        # isn't careful. If it's the background hub that winds up capturing
        # the hub, it will ask the hub to switch back to itself and
        # then switch to the hub, which will raise LoopExit (nothing
        # for the background thread to do). What is supposed to happen
        # is that the background thread realizes it's the background thread,
        # starts an async watcher and then switches to the hub.
        #
        # So we deliberately don't set the hub to help test that condition.
        return lock.RLock()

    def assertOneHasNoHub(self, sem):
        self.assertIsNone(sem._block.hub)



if __name__ == '__main__':
    greentest.main()
