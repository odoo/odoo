import inspect

from .common import RegistryLintCase

DEPRECATED_MODEL_ATTRIBUTES = [
    ('view_init', ''),
    ('_needaction', ''),
    ('_sql', "use _table or _table_query"),
    ('_execute_sql', "use self.env.execute_query"),
    ('name_get', "overwrite `_compute_display_name`")
]


class TestModelDeprecations(RegistryLintCase):
    failureException = TypeError

    def test_model_attributes(self):
        for model_name, Model in self.registry.items():
            for attr, detail_message in DEPRECATED_MODEL_ATTRIBUTES:
                with self.subTest(model=model_name, attr=attr):
                    value = getattr(Model, attr, None)
                    if value is None:
                        continue
                    msg = f"Deprecated method/attribute {model_name}.{attr}"
                    module = inspect.getmodule(value)
                    if module:
                        msg += f" in {module}"
                    if detail_message:
                        msg += ", " + detail_message
                    self.fail(msg)

    def test_parameter_rpc_compatible(self):
        """Parameters "ids" and "context" are not allowed in public methods.
        These conflict with standard parameters used in RPC calls.
        """
        INVALID_NAMES = {'ids', 'context'}
        for model_name, model_cls in self.registry.items():
            for method_name, method in inspect.getmembers(model_cls, inspect.isroutine):
                if method_name.startswith('_') or getattr(method, '_api_private', False):
                    continue

                with self.subTest(model=model_name, method=method_name):
                    signature = inspect.signature(method)
                    self.assertFalse(INVALID_NAMES.intersection(signature.parameters), "Invalid parameter names found")
