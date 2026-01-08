# test for issue #210
from gevent import core
from gevent.testing.util import alarm


alarm(1)

log = []
loop = core.loop(default=False)
loop.run_callback(log.append, 1)
loop.run()
assert log == [1], log
