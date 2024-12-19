from odoo import models, _
from odoo.exceptions import ValidationError


class IrUiView(models.Model):
    _inherit = ['ir.ui.view']

    def _postprocess_view(self, node, model_name, editable=True, node_info=None, **options):
        model = self.env[model_name]
        country_code = 'country_code' if 'country_code' in model._fields else f"'{self.env.company.country_id.code}'"
        for elem in node.xpath('.//*[@l10n]'):
            l10n_attr_value = elem.get('l10n').upper()
            if len(l10n_attr_value) != 2 or not l10n_attr_value.isalpha():
                raise ValidationError(_('l10n attribute must be a valid 2 letter country code e.g. "BE"'))
            modifier = 'column_invisible' if elem.tag == 'field' and self.type == 'list' else 'invisible'
            existing_condition = ''
            if rule := elem.get(modifier):
                existing_condition = '(' + rule + ') and '
            print(existing_condition + f"{country_code} != '{l10n_attr_value}'")
            elem.set(modifier, existing_condition + f"{country_code} != '{l10n_attr_value}'")

        return super()._postprocess_view(node, model_name, editable=editable, node_info=node_info, **options)
