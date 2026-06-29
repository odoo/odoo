from gevent import monkey
import threading
# Make sure that we can patch gevent while holding
# a threading lock. Under Python2, where RLock is implemented
# in python code, this used to throw RuntimeErro("Cannot release un-acquired lock")
# See https://github.com/gevent/gevent/issues/615
# pylint:disable=useless-with-lock
with threading.RLock():
    monkey.patch_all() # pragma: testrunner-no-monkey-combine
