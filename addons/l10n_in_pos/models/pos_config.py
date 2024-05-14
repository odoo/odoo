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
        for vals in list(vals_list):
            if self.env.company.country_code == 'IN':
                vals.update({
                    'is_closing_entry_by_product': True
                })
        pos_configs = super().create(vals_list)
        return pos_configs
