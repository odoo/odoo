from __future__ import print_function
# This file makes this directory into a runnable package.
# it exists to test 'python -m gevent.monkey monkey_package'
# Note that the __file__ may differ slightly; starting with
# Python 3.9, directly running it gets an abspath, but
# using ``runpy`` doesn't.
import os.path
print(os.path.abspath(__file__))
print(__name__)
