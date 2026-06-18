# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class PosConfig(models.Model):
    _inherit = 'pos.config'

    # NOTE: this function acts as a m2m field with loyalty.program model. We do this to handle an exceptional use case:
    # When no PoS is specified at a loyalty program form, this program is applied to every PoS (instead of none)
    def _get_program_ids(self, check_usage=True):
        today = fields.Date.context_today(self)
        programs = self.env['loyalty.program'].search([
            ('pos_ok', '=', True),
            '|', ('pos_config_ids', '=', self.id), ('pos_config_ids', '=', False),
            '|', ('date_from', '=', False), ('date_from', '<=', today),
            '|', ('date_to', '=', False), ('date_to', '>=', today),
            '|', ('pricelist_ids', '=', False), ('pricelist_ids', 'in', self._get_available_pricelists().ids),
            ('currency_id', '=', self.currency_id.id)
        ])

        if check_usage:
            programs = programs.filtered(
                lambda p: not p.limit_usage or p.sudo().total_order_count < p.max_usage
            )
        return programs
