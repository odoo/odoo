# -*- coding: utf-8 -*-
"""
Test for issue #1526:
- dnspython is imported first;
- monkey-patching happens early
"""
from __future__ import print_function, absolute_import

from gevent import monkey
monkey.patch_all()
# pylint:disable=import-error
import dns
assert dns

import socket
import sys

socket.getfqdn()

import gevent.resolver.dnspython
from gevent.resolver.dnspython import dns as gdns
from dns import rdtypes # NOT import dns.rdtypes

assert gevent.resolver.dnspython.dns is gdns
assert gdns is not dns, (gdns, dns, "id dns", id(dns))
assert gdns.rdtypes is not rdtypes, (gdns.rdtypes, rdtypes)
assert hasattr(dns, 'rdtypes')
print(sorted(sys.modules))
