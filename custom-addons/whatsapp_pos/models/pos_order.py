# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models


class PosOrder(models.Model):
    _inherit = 'pos.order'

    def action_sent_receipt_on_whatsapp(self, name, partner, ticket_image):
        """ Send receipt on whatsapp if whatsapp is enabled and partner has whatsapp number or number is provided."""
        if not self or not self.config_id.whatsapp_enabled or not self.config_id.receipt_template_id or not partner.get('whatsapp'):
            return
        self.ensure_one()
        filename = 'Receipt-' + name + '.jpg'
        receipt = self.env['ir.attachment'].create({
            'name': filename,
            'type': 'binary',
            'datas': ticket_image,
            'res_model': 'pos.order',
            'res_id': self.ids[0],
            'mimetype': 'image/jpeg',
        })
        whatsapp_composer = self.env['whatsapp.composer'].with_context({'active_id': self.id}).create(
            {
                'attachment_id': receipt.id,
                'phone': partner['whatsapp'],
                'wa_template_id': self.config_id.receipt_template_id.id,
                'res_model': 'pos.order'
            }
        )
        whatsapp_composer._send_whatsapp_template()
        if self.to_invoice and self.config_id.invoice_template_id:
            whatsapp_composer = self.env['whatsapp.composer'].with_context({'active_id': self.account_move.id}).create(
                {
                    'phone': partner['whatsapp'],
                    'wa_template_id': self.config_id.invoice_template_id.id,
                    'res_model': 'account.move'
                }
            )
            # Receipt is already send so force_send_by_cron is True
            # so it's not raise error if there is any miss configuration
            whatsapp_composer._send_whatsapp_template(force_send_by_cron=True)

    def _get_whatsapp_safe_fields(self):
        return {'partner_id.name', 'name', 'company_id.name'}

    def _mail_get_partners(self):
        return {pos_order.id: pos_order.partner_id for pos_order in self}
