# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import logging
import os
import re
import subprocess
from unittest import skipIf
from odoo import tools
from odoo.modules import get_modules, get_module_path

from . import lint_case

MAX_ES_VERSION = 'es8'

_logger = logging.getLogger(__name__)

try:
    es_check = tools.misc.find_in_path('es-check')
except IOError:
    es_check = None


@skipIf(es_check is None, "es-check tool not found on this system")
class TestECMAScriptVersion(lint_case.LintCase):

    longMessage = True

    def test_ecmascript_version(self):
        """ Test that there is no unsupported ecmascript in javascript files """

        black_re = re.compile(r'summernote.+(intro\.js|outro.js)$')

        files_to_check = [
            p for p in self.iter_module_files('*.js')
            if not 'static/test' in p
            if not 'static/src/tests' in p
            if not black_re.search(p)
        ]

        _logger.info('Testing %s js files', len(files_to_check))
        cmd = [es_check, MAX_ES_VERSION] + files_to_check
        process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        out, err = process.communicate()
        self.assertEqual(process.returncode, 0, msg=out.decode())
