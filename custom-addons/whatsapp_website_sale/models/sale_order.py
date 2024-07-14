# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    def action_confirm(self):
        res = super().action_confirm()
        for order in self.filtered(lambda o: o.website_id.wa_sale_template_id):
            whatsapp_composer = self.env['whatsapp.composer'].with_context({'active_id': order.id}).create(
                {
                    'wa_template_id': order.website_id.wa_sale_template_id.id,
                    'res_model': 'sale.order'
                }
            )
            whatsapp_composer.sudo()._send_whatsapp_template(force_send_by_cron=True)
        return res
