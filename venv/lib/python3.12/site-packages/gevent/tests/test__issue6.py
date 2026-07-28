from __future__ import print_function
from __future__ import absolute_import
from __future__ import division

import sys

if not sys.argv[1:]:
    from subprocess import Popen, PIPE
    # not on Py2 pylint:disable=consider-using-with
    p = Popen([sys.executable, __file__, 'subprocess'], stdin=PIPE, stdout=PIPE, stderr=PIPE)
    out, err = p.communicate(b'hello world\n')
    code = p.poll()
    assert p.poll() == 0, (out, err, code)
    assert out.strip() == b'11 chars.', (out, err, code)
    # XXX: This is seen sometimes to fail on Travis with the following value in err but a code of 0;
    # it seems load related:
    #  'Unhandled exception in thread started by \nsys.excepthook is missing\nlost sys.stderr\n'.
    # If warnings are enabled, Python 3 has started producing this:
    # '...importlib/_bootstrap.py:219: ImportWarning: can't resolve package from __spec__
    #    or __package__, falling back on __name__ and __path__\n  return f(*args, **kwds)\n'
    assert err == b'' or b'sys.excepthook' in err or b'Warning' in err, (out, err, code)

elif sys.argv[1:] == ['subprocess']: # pragma: no cover
    import gevent
    import gevent.monkey
    gevent.monkey.patch_all(sys=True)

    def printline():
        try:
            line = raw_input()
        except NameError:
            line = input() # pylint:disable=bad-builtin
        print('%s chars.' % len(line))
        sys.stdout.flush()

    gevent.spawn(printline).join()

else: # pragma: no cover
    sys.exit('Invalid arguments: %r' % (sys.argv, ))
