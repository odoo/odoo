import logging
import subprocess
import sys
import time
from pathlib import Path

from odoo.tests import BaseCase

_logger = logging.getLogger(__name__)


class TestInit(BaseCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.python_path = Path(__file__).parents[4].resolve()

    def run_python(self, code, check=True, capture_output=True, text=True, timeout=10, env=None, **kwargs):
        code = code.replace('\n', '; ')
        env = {
            **(env or {}),
            "PYTHONPATH": str(self.python_path),
        }
        # disable warnings for frozen_modules when debugger is running
        return subprocess.run(
            [sys.executable, '-c', code],
            capture_output=capture_output,
            check=check,
            env=env,
            text=text,
            timeout=timeout,
            **kwargs
        )

    def odoo_modules_to_test(self):
        import odoo.cli  # noqa: PLC0415
        for path in (*odoo.__path__, *odoo.cli.__path__):
            parent = Path(path)
            for module in parent.iterdir():
                if (module.is_dir() or module.suffix == '.py') and '__' not in module.name:
                    if parent.name == 'odoo':
                        yield f"odoo.{module.stem}"
                    else:
                        yield f"odoo.{parent.name}.{module.stem}"

    def test_import(self):
        """Test that importing a sub-module in any order works."""
        EXPECT_UTC = ('init', 'cli', 'http', 'modules', 'service', 'api', 'fields', 'models', 'orm', 'tests')
        for module in sorted(self.odoo_modules_to_test()):
            set_timezone = any(expect in module for expect in EXPECT_UTC)
            env = {'TZ': 'CET'}
            timezone = 'UTC' if set_timezone else 'CET'
            code = f"import {module}; import sys, time; sys.exit(0 if (time.tzname[0] == '{timezone}') else 5)"
            with self.subTest(module=module, timezone=timezone):
                start_time = time.perf_counter()
                self.run_python(code, env=env, check=False)
                end_time = time.perf_counter()
                _logger.info("  %s execution time: %.3fs", module, end_time - start_time)
