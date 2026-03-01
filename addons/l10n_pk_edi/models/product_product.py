import re

from odoo import api, models


class ProductProduct(models.Model):
    _inherit = 'product.product'

    @api.model
    def get_compiled_regex(self):
        return re.compile(self.env.ref('l10n_pk_edi.l10n_pk_edi_hs_code_reg').value)

    # -------------------------------------------------------------------------
    # Validation Methods
    # -------------------------------------------------------------------------

    def _group_by_error_code(self):
        self.ensure_one()
        if any(not self[field] for field in ('hs_code', 'l10n_pk_edi_sale_type')):
            return (
                ('message', self.env._('Product(s) must have a HS Code, and Sale Type.')),
                ('error_code', 'product_value_missing'),
                ('level', 'danger'),
            )
        hs_code_regex = self.get_compiled_regex()
        if self.hs_code and not hs_code_regex.match(self.hs_code):
            return (
                ('message', self.env._('Product(s) has an invalid HS Code. It must follow the format 0000.0000 which is 8 digits with a dot in the middle.')),
                ('error_code', 'product_hscode_invalid'),
                ('level', 'danger'),
            )

        return False

    def _l10n_pk_edi_export_check(self):
        """Validate Product for E-Invoicing compliance."""
        alert_vals = {}
        for error_tuple, invalid_records in self.grouped(lambda m: m._group_by_error_code()).items():
            if not error_tuple:
                continue
            temp_dict = dict(error_tuple)
            alert_vals.update({
                temp_dict['error_code']: {
                    'message': temp_dict['message'],
                    'level': temp_dict['level'],
                    'action': invalid_records._get_records_action(),
                    'action_text':  self.env._('View Product(s)'),
                },
            })
        return alert_vals
