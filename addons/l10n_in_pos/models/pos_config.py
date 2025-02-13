# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import api, models
from odoo.exceptions import UserError
from odoo.tools.translate import _


class PosConfig(models.Model):
    _inherit = 'pos.config'

    @api.constrains('is_closing_entry_by_product')
    def _check_journal_entry_with_product_line(self):
        for config in self:
            if config.company_id.country_code == 'IN' and not config.is_closing_entry_by_product:
                raise UserError(_("You can't deactivate the 'Closing Entry by product' option for Indian Companies."))

    @api.model_create_multi
    def create(self, vals_list):
        pos_configs = super().create(vals_list)
        indian_pos_config = pos_configs.filtered(lambda config: config.company_id.account_fiscal_country_id.code == "IN")
        indian_pos_config.write({
            'is_closing_entry_by_product': True
        })
        return pos_configs
