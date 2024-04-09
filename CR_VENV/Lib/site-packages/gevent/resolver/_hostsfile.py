# -*- coding: utf-8 -*-
# Copyright (c) 2019  gevent contributors. See LICENSE for details.
#
# Portions of this code taken from dnspython
#   https://github.com/rthalley/dnspython
#
# Copyright (C) Dnspython Contributors, see LICENSE for text of ISC license

# Copyright (C) 2003-2017 Nominum, Inc.
#
# Permission to use, copy, modify, and distribute this software and its
# documentation for any purpose with or without fee is hereby granted,
# provided that the above copyright notice and this permission notice
# appear in all copies.
#
# THE SOFTWARE IS PROVIDED "AS IS" AND NOMINUM DISCLAIMS ALL WARRANTIES
# WITH REGARD TO THIS SOFTWARE INCLUDING ALL IMPLIED WARRANTIES OF
# MERCHANTABILITY AND FITNESS. IN NO EVENT SHALL NOMINUM BE LIABLE FOR
# ANY SPECIAL, DIRECT, INDIRECT, OR CONSEQUENTIAL DAMAGES OR ANY DAMAGES
# WHATSOEVER RESULTING FROM LOSS OF USE, DATA OR PROFITS, WHETHER IN AN
# ACTION OF CONTRACT, NEGLIGENCE OR OTHER TORTIOUS ACTION, ARISING OUT
# OF OR IN CONNECTION WITH THE USE OR PERFORMANCE OF THIS SOFTWARE.
"""
Private support for parsing /etc/hosts.

"""
from __future__ import absolute_import, division, print_function

import sys
import os
import re

from gevent.resolver._addresses import is_ipv4_addr
from gevent.resolver._addresses import is_ipv6_addr

from gevent._compat import iteritems


class HostsFile(object):
    """
    A class to read the contents of a hosts file (/etc/hosts).
    """

    LINES_RE = re.compile(r"""
        \s*  # Leading space
        ([^\r\n#]+?)  # The actual match, non-greedy so as not to include trailing space
        \s*  # Trailing space
        (?:[#][^\r\n]+)?  # Comments
        (?:$|[\r\n]+)  # EOF or newline
    """, re.VERBOSE)

    def __init__(self, fname=None):
        self.v4 = {} # name -> ipv4
        self.v6 = {} # name -> ipv6
        self.aliases = {} # name -> canonical_name
        self.reverse = {} # ip addr -> some name
        if fname is None:
            if os.name == 'posix':
                fname = '/etc/hosts'
            elif os.name == 'nt': # pragma: no cover
                fname = os.path.expandvars(
                    r'%SystemRoot%\system32\drivers\etc\hosts')
        self.fname = fname
        assert self.fname
        self._last_load = 0


    def _readlines(self):
        # Read the contents of the hosts file.
        #
        # Return list of lines, comment lines and empty lines are
        # excluded. Note that this performs disk I/O so can be
        # blocking.
        with open(self.fname, 'rb') as fp:
            fdata = fp.read()


        # XXX: Using default decoding. Is that correct?
        udata = fdata.decode(errors='ignore') if not isinstance(fdata, str) else fdata

        return self.LINES_RE.findall(udata)

    def load(self): # pylint:disable=too-many-locals
        # Load hosts file

        # This will (re)load the data from the hosts
        # file if it has changed.

        try:
            load_time = os.stat(self.fname).st_mtime
            needs_load = load_time > self._last_load
        except (IOError, OSError):
            from gevent import get_hub
            get_hub().handle_error(self, *sys.exc_info())
            needs_load = False

        if not needs_load:
            return

        v4 = {}
        v6 = {}
        aliases = {}
        reverse = {}

        for line in self._readlines():
            parts = line.split()
            if len(parts) < 2:
                continue
            ip = parts.pop(0)
            if is_ipv4_addr(ip):
                ipmap = v4
            elif is_ipv6_addr(ip):
                if ip.startswith('fe80'):
                    # Do not use link-local addresses, OSX stores these here
                    continue
                ipmap = v6
            else:
                continue
            cname = parts.pop(0).lower()
            ipmap[cname] = ip
            for alias in parts:
                alias = alias.lower()
                ipmap[alias] = ip
                aliases[alias] = cname

            # XXX: This is wrong for ipv6
            if ipmap is v4:
                ptr = '.'.join(reversed(ip.split('.'))) + '.in-addr.arpa'
            else:
                ptr = ip + '.ip6.arpa.'
            if ptr not in reverse:
                reverse[ptr] = cname

        self._last_load = load_time
        self.v4 = v4
        self.v6 = v6
        self.aliases = aliases
        self.reverse = reverse

    def iter_all_host_addr_pairs(self):
        self.load()
        for name, addr in iteritems(self.v4):
            yield name, addr
        for name, addr in iteritems(self.v6):
            yield name, addr
