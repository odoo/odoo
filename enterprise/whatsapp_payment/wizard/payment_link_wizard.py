# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models


class PaymentLinkWizard(models.TransientModel):
    _inherit = "payment.link.wizard"

    # UX field used to display the send whatsapp button
    can_send_whatsapp = fields.Boolean(string="Can Send WhatsApp", compute="_compute_can_send_whatsapp")

    @api.depends('res_model')
    @api.depends_context('uid')
    def _compute_can_send_whatsapp(self):
        self.can_send_whatsapp = self.env['whatsapp.template']._can_use_whatsapp('payment.link.wizard')

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
