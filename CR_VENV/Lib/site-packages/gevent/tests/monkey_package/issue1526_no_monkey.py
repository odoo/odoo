# -*- coding: utf-8 -*-
"""
Test for issue #1526:
- dnspython is imported first;
- no monkey-patching is done.
"""
from __future__ import print_function
from __future__ import absolute_import

import dns # pylint:disable=import-error
assert dns
import gevent.socket as socket # pylint:disable=consider-using-from-import
socket.getfqdn() # create the resolver

from gevent.resolver.dnspython import dns as gdns
import dns.rdtypes # pylint:disable=import-error

assert dns is not gdns, (dns, gdns)
assert dns.rdtypes is not gdns.rdtypes
import sys
print(sorted(sys.modules))
