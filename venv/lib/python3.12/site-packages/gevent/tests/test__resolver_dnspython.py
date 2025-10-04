# -*- coding: utf-8 -*-
"""
Tests explicitly using the DNS python resolver.

"""
from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

import sys
import unittest
import subprocess
import os

from gevent import testing as greentest

@unittest.skipUnless(greentest.resolver_dnspython_available(),
                     "dnspython not available")
class TestDnsPython(unittest.TestCase):

    def _run_one(self, mod_name):
        cmd = [
            sys.executable,
            '-m',
            'gevent.tests.monkey_package.' + mod_name
        ]

        env = dict(os.environ)
        env['GEVENT_RESOLVER'] = 'dnspython'

        output = subprocess.check_output(cmd, env=env)
        self.assertIn(b'_g_patched_module_dns', output)
        self.assertNotIn(b'_g_patched_module_dns.rdtypes', output)
        return output

    def test_import_dns_no_monkey_patch(self):
        self._run_one('issue1526_no_monkey')

    def test_import_dns_with_monkey_patch(self):
        self._run_one('issue1526_with_monkey')

if __name__ == '__main__':
    greentest.main()
