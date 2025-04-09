# Part of Odoo. See LICENSE file for full copyright and licensing details.

import inspect

from odoo.tests.common import TransactionCase, tagged

DEPRECATED_MODEL_ATTRIBUTES = [
    'view_init',
    '_needaction',
    '_sql',
    '_execute_sql',
]


@tagged('-at_install', 'post_install', 'deprecation')
class TestModelDeprecations(TransactionCase):

    def test_model_attributes(self):
        for model_name, Model in self.registry.items():
            for attr in DEPRECATED_MODEL_ATTRIBUTES:
                with self.subTest(model=model_name, attr=attr):
                    value = getattr(Model, attr, None)
                    if value is None:
                        continue
                    msg = f"Deprecated method/attribute {model_name}.{attr}"
                    module = inspect.getmodule(value)
                    if module:
                        msg += f" in {module}"
                    self.fail(msg)

    def test_name_get(self):
        for model_name, Model in self.registry.items():
            with self.subTest(model=model_name):
                if not hasattr(Model, 'name_get'):
                    continue
                module = inspect.getmodule(Model.name_get)
                self.fail(f"Deprecated name_get method found on {model_name} in {module.__name__}, you should override `_compute_display_name` instead")

    def test_multi_search(self):
        for model_name, Model in self.registry.items():
            if Model._abstract:
                continue
            model = Model(self.env, (), ())
            aggregates = [
                f'{fname}:{aggregator}' for fname, field in model._fields.items()
                if (aggregator := field._description_aggregator(model.env))
            ]
            aggregates.append('__count')
            for field in model._fields.values():
                if 'properties' in field.type:
                    continue
                if not field._description_groupable(model.env):
                    continue
                if field.type in ('datetime', 'date'):
                    groupby = f"{field.name}:month"
                else:
                    groupby = field.name

                groups = model.formatted_read_group([], [groupby], aggregates, having=[('__count', '>', 10)], limit=10)
                if len(groups) <= 1:
                    continue
                with self.env.cr._enable_logging():
                    model.multi_search([], [group['__extra_domain'] for group in groups], group_limit=40)