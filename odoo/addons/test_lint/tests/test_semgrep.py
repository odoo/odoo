import contextlib
import logging
import pathlib
import subprocess
import unittest

import odoo.tools
import odoo.addons
from odoo.tests import TransactionCase, tagged
from odoo.tests.common import _preexec, no_retry
from odoo.tools.which import which

_logger = logging.getLogger(__name__)

RULES = pathlib.Path(__file__, '..', 'rules').resolve().absolute()


@tagged('at_install', '-post_install')
@no_retry
class TestSemgrep(TransactionCase):
    def test_semgrep(self) -> None:
        semgrep = 'semgrep'
        with contextlib.suppress(IOError):
            semgrep = which('semgrep')
        try:
            r = subprocess.run([semgrep, '--version'], stdout=subprocess.PIPE, encoding='utf-8')
            _logger.runbot("semgrep version %s", r.stdout.strip() or '???')
            r = subprocess.run([
                semgrep,
                'scan',
                '-j', '1',
                '-q',
                '--x-ignore-semgrepignore-files',
                '--disable-version-check',
                '--error',
                '-c', RULES,
                odoo.tools.config.root_path,
                *(
                    pathlib.Path(p).resolve()
                    for p in odoo.addons.__path__
                ),
            ], preexec_fn=_preexec, encoding='utf-8', capture_output=True, check=False)
        except FileNotFoundError:
            _logger.warning("semgrep not found int PATH")
            raise unittest.SkipTest("semgrep not found in PATH")
        else:
            if r.returncode:
                self.fail(f"semgrep failed\n\n{r.stdout}\n{r.stderr}".strip())

    def test_semgrep_rules(self) -> None:
        semgrep = 'semgrep'
        with contextlib.suppress(IOError):
            semgrep = which('semgrep')
        try:
            r = subprocess.run([
                semgrep,
                'scan',
                '--disable-version-check',
                '--test',
                RULES
            ], preexec_fn=_preexec, encoding='utf-8', capture_output=True, check=False)
        except FileNotFoundError:
            raise unittest.SkipTest("semgrep not found in PATH")
        else:
            if r.returncode:
                self.fail(f"semgrep failed\n\n{r.stdout}\n{r.stderr}".strip())
