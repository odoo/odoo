import os
import sys
import gevent
import gevent.core
import subprocess

if not sys.argv[1:]:
    os.environ['GEVENT_BACKEND'] = 'select'
    # (not in Py2) pylint:disable=consider-using-with
    popen = subprocess.Popen([sys.executable, __file__, '1'])
    assert popen.wait() == 0, popen.poll()
else: # pragma: no cover
    hub = gevent.get_hub()
    if 'select' in gevent.core.supported_backends():
        assert hub.loop.backend == 'select', hub.loop.backend
    else:
        # libuv isn't configurable
        assert hub.loop.backend == 'default', hub.loop.backend
