from odoo import models


class PosOrder(models.Model):
    _inherit = 'pos.order'

    def _prepare_product_aml_dict(self, base_line_vals, update_base_line_vals, rate, sign):
        aml_dict = super()._prepare_product_aml_dict(base_line_vals, update_base_line_vals, rate, sign)
        aml_dict['no_followup'] = False
        return aml_dict
