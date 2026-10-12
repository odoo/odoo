import inspect
import logging

from .common import RegistryLintCase

_logger = logging.getLogger(__name__)


class TestMethodsOverrideTranslatedFields(RegistryLintCase):
    WRITE_CHECKED_FIELD_NAMES = {  # {module_name: [model_name.field_name, ...]}
        'base': ['res.groups.name'],
        'web_studio': ['ir.ui.menu.name'],
        'website_sale': ['product.template.description_ecommerce'],
        'point_of_sale': ['product.template.public_description', 'product.tag.pos_description'],
        'project': ['project.project.name'],
        'account': ['account.journal.name'],
        'documents': ['documents.document.name'],
        'im_livechat': ['chatbot.script.title'],
        'documents_project': ['project.project.name'],
        'website_slides': ['slide.channel.description'],
    }

    def test_write_override_translated_field(self):
        base_write = self.registry['base'].write
        violations = []
        modules_to_check = self.registry._init_modules & set(self.WRITE_CHECKED_FIELD_NAMES)
        checked_field_names = {
            module_name: field_names.copy()
            for module_name, field_names in self.WRITE_CHECKED_FIELD_NAMES.items()
            if module_name in modules_to_check
        }
        for model in self.registry.values():
            if model.write is base_write:
                continue
            translated_field_names = [
                field.name for field in model._fields.values() if field.translate
            ]
            if not translated_field_names:
                continue
            for cls in model.__mro__:
                if 'write' not in cls.__dict__:
                    continue
                write_method = cls.__dict__['write']
                if write_method is base_write:
                    break
                source = inspect.getsource(write_method)
                for field_name in translated_field_names:
                    full_name = f'{model._name}.{field_name}'
                    patterns = [
                        f"vals['{field_name}']",
                        f'vals["{field_name}"]',
                        f"vals.get('{field_name}'",
                        f'vals.get("{field_name}"',
                    ]
                    if matched_pattern := next(iter(p for p in patterns if p in source), None):
                        module_name = cls.__module__.split('.')[2]  # odoo.addons.module_name.xxx
                        if full_name in checked_field_names.get(module_name, []):
                            checked_field_names[module_name].remove(full_name)
                        else:
                            violations.append(
                                f"find pattern {matched_pattern} in the write method of model {model._name} ({cls.__module__})"
                            )

        checked_field_names = {k: v for k, v in checked_field_names.items() if v}
        if checked_field_names:
            _logger.warning("Some checked fields maybe not be used in the write anymore %s", checked_field_names)
        self.assertFalse(len(violations), "Override `write`(maybe also `create`) for translated fields \n" + '\n'.join(violations))

    COPY_DATA_CHECKED_FIELD_NAMES = {  # {module_name: [model_name.field_name, ...]}
        # Prefer Field.copy callables (e.g. mark_as_copy) over copy_data overrides.
        # List intentional exceptions that still touch translated fields in copy_data
        # without using mark_as_copy / adapt_translated_field_value.
    }

    def test_copy_data_override_translated_field(self):
        base_copy_data = self.registry['base'].copy_data
        violations = []
        modules_to_check = self.registry._init_modules & set(self.COPY_DATA_CHECKED_FIELD_NAMES)
        checked_field_names = {
            module_name: field_names.copy()
            for module_name, field_names in self.COPY_DATA_CHECKED_FIELD_NAMES.items()
            if module_name in modules_to_check
        }
        for model in self.registry.values():
            if model.copy_data is base_copy_data:
                continue
            translated_field_names = [
                field.name for field in model._fields.values() if field.translate
            ]
            if not translated_field_names:
                continue
            for cls in model.__mro__:
                if 'copy_data' not in cls.__dict__:
                    continue
                copy_data_method = cls.__dict__['copy_data']
                if copy_data_method is base_copy_data:
                    break
                source = inspect.getsource(copy_data_method)
                for field_name in translated_field_names:
                    full_name = f'{model._name}.{field_name}'
                    patterns = [
                        f"['{field_name}']",
                        f'["{field_name}"]',
                        f".get('{field_name}'",
                        f'.get("{field_name}"',
                        f"{field_name}=",
                    ]
                    if matched_pattern := next(iter(p for p in patterns if p in source), None):
                        if (
                            f"['{field_name}'] = adapt_translated_field_value(" in source
                            or f'["{field_name}"] = adapt_translated_field_value(' in source
                            or f"['{field_name}'] = mark_as_copy(" in source
                            or f'["{field_name}"] = mark_as_copy(' in source
                        ):
                            # simple stupid skip for adapt_translated_field_value / mark_as_copy
                            continue
                        module_name = cls.__module__.split('.')[2]  # odoo.addons.module_name.xxx
                        if full_name in checked_field_names.get(module_name, []):
                            checked_field_names[module_name].remove(full_name)
                        else:
                            violations.append(
                                f"find pattern {matched_pattern} in the copy_data method of model {model._name} ({cls.__module__})"
                            )

        checked_field_names = {k: v for k, v in checked_field_names.items() if v}
        if checked_field_names:
            _logger.warning("Some checked fields maybe not be used in the copy_data anymore %s", checked_field_names)
        self.assertFalse(len(violations), "Override `copy_data` for translated fields \n" + '\n'.join(violations))
