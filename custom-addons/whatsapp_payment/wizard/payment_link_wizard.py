# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models


class PaymentLinkWizard(models.TransientModel):
    _inherit = "payment.link.wizard"

    def action_send_whatsapp(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'whatsapp.composer',
            'view_mode': 'form',
            'target': 'new',
            'context': {'default_res_id': self.id, 'default_res_model': 'payment.link.wizard'}
        }

    def _get_whatsapp_safe_fields(self):
        return {'partner_id.name', 'currency_id.symbol', 'amount', 'company_id.name', 'description', 'link'}
