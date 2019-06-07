# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import logging
import os
import re
import subprocess
from unittest import skipIf
from odoo.tests.common import TransactionCase
from odoo import tools
from odoo.modules import get_modules, get_module_path

MAX_ES_VERSION = 'es5'

_logger = logging.getLogger(__name__)

try:
    es_check = tools.misc.find_in_path('es-check')
except IOError:
    es_check = None


@skipIf(es_check is None, "es-check tool not found on this system")
class TestECMAScriptVersion(TransactionCase):

    longMessage = True

    def test_ecmascript_version(self):
        """ Test that there is no unsupported ecmascript in javascript files """

        black_re = re.compile(r'summernote.+(intro\.js|outro.js)$')

        mod_paths = [get_module_path(m) for m in get_modules()]
        files_to_check = []
        for p in mod_paths:
            for dp, _, file_names in os.walk(p):
                if 'static/test' in dp:
                    continue
                for fn in file_names:
                    fullpath_name = os.path.join(dp, fn)
                    if fullpath_name.endswith('.js') and not black_re.search(fullpath_name):
                        files_to_check.append(fullpath_name)

        _logger.info('Testing %s js files', len(files_to_check))
        cmd = [es_check, MAX_ES_VERSION] + files_to_check
        process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        out, err = process.communicate()
        self.assertEqual(process.returncode, 0, msg=out)
