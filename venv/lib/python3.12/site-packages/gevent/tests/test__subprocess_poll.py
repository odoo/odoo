import sys
# XXX: Handle this more automatically. See comments in the testrunner.
from gevent.testing.resources import exit_without_resource
exit_without_resource('subprocess')

from gevent.subprocess import Popen
from gevent.testing.util import alarm

alarm(3)

popen = Popen([sys.executable, '-c', 'pass'])
while popen.poll() is None:
    pass
