import gevent
from gevent.testing.util import alarm


alarm(3)


with gevent.Timeout(0.01, False):
    while True:
        gevent.sleep(0)
