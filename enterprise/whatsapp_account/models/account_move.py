# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models


class AccountMove(models.Model):
    _inherit = 'account.move'

    def _get_whatsapp_safe_fields(self):
        return {'partner_id.name', 'name', 'company_id.name', 'currency_id.symbol', 'amount'}
