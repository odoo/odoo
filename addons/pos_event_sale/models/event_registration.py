# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import models, api


class EventRegistration(models.Model):
    _inherit = ['event.registration']

    @api.depends('pos_order_id.state')
    def _compute_registration_status(self):
        super()._compute_registration_status()
        for record in self.filtered("pos_order_id.id"):
            if record.pos_order_id.state in ['paid', 'done', 'invoiced']:
                record.sale_status = 'sold'
                record.state = 'done'
            else:
                record.sale_status = 'to_pay'
                record.state = 'draft'
