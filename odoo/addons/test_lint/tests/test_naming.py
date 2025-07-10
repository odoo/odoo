import inspect

from odoo.modules.registry import Registry
from odoo.tests.common import get_db_name, tagged

from .lint_case import LintCase


@tagged('-at_install', 'post_install')
class TestNaming(LintCase):
    failureException = TypeError

    def test_parameter_rpc_compatible(self):
        """Parameters "ids" and "context" are not allowed in public methods.
        These conflict with standard parameters used in RPC calls.
        """
        INVALID_NAMES = {'ids', 'context'}
        registry = Registry(get_db_name())

        for model_name, model_cls in registry.items():
            for method_name, method in inspect.getmembers(model_cls, inspect.isroutine):
                if method_name.startswith('_') or getattr(method, '_api_private', False):
                    continue

                with self.subTest(model=model_name, method=method_name):
                    signature = inspect.signature(method)
                    self.assertFalse(INVALID_NAMES.intersection(signature.parameters), "Invalid parameter names found")
