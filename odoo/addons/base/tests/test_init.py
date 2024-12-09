import subprocess
import sys
from pathlib import Path

import odoo
from odoo.tests import BaseCase


class TestInit(BaseCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.python_path = Path(__file__).parents[4].resolve()

    def run_python(self, code, check=True, capture_output=True, text=True, timeout=10, **kwargs):
        code = code.replace('\n', '; ')
        env = {
            "PYTHONPATH": str(self.python_path),
        }
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
        for path in odoo.__path__:
            for module in Path(path).iterdir():
                if (module.is_dir() or module.suffix == '.py') and '__' not in module.name:
                    yield module.stem

    def test_import(self):
        """Test that importing a sub-module in any order works."""
        for module_name in self.odoo_modules_to_test():
            module = f"odoo.{module_name}"
            with self.subTest(module=module):
                self.run_python(f'import {module}')
