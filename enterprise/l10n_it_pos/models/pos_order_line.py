from odoo import models, fields


class PosOrderLine(models.Model):
    _inherit = 'pos.order.line'

    def _prepare_base_line_for_taxes_computation(self):
        # OVERRIDE 'point_of_sale'
        base_line = super()._prepare_base_line_for_taxes_computation()
        country_code = self.company_id.account_fiscal_country_id.code
        config = self.order_id.config_id
        base_line['l10n_it_epson_printer'] = country_code == 'IT' and config.it_fiscal_printer_ip
        return base_line
