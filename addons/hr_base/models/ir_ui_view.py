from odoo import models


class IrUiView(models.Model):
    _inherit = ['ir.ui.view']

    def _postprocess_view(self, node, model_name, editable=True, node_info=None, **options):
        model = self.env[model_name]
    
        for elem in node.xpath('.//*[@l10n]'):
            l10n_attr_value = self._convert_l10n(elem.get('l10n')).upper()
            assert len(l10n_attr_value) == 2 and l10n_attr_value.isalpha(), 'l10n attribute must be a valid 2 letter country code e.g. "BE"'
            existing_condition = ''
            if rule := elem.get(modifier):
                existing_condition = '(' + rule + ') and '
            elem.set(modifier, existing_condition + f"'{self.env.company.country_id.code}' != '{l10n_attr_value}'")

        return super()._postprocess_view(node, model_name, editable=editable, node_info=node_info, **options)        