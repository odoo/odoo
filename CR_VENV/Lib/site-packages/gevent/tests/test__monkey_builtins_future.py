# Under Python 2,  if the `future` module is installed, we get
# a `builtins` module, which mimics the `builtins` module from
# Python 3, but does not have the __import__ and some other functions.
# Make sure we can still run in that case.
import sys
try:
    # fake out a "broken" builtins module
    import builtins
except ImportError:
    class builtins(object):
        pass
    sys.modules['builtins'] = builtins()

if not hasattr(builtins, '__import__'):
    import gevent.monkey
    gevent.monkey.patch_builtins()
