# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class LoyaltyHistory(models.Model):
    _name = 'loyalty.history'
    _description = "History for Loyalty cards and Ewallets"
    _order = 'id desc'

    card_id = fields.Many2one(comodel_name='loyalty.card', required=True, ondelete='cascade')
    company_id = fields.Many2one(related='card_id.company_id')

    description = fields.Text(required=True)

    issued = fields.Float()
    used = fields.Float()

    order_model = fields.Char(readonly=True)
    order_id = fields.Many2oneReference(model_field='order_model', readonly=True)

    def _get_order_portal_url(self):
        self.ensure_one()
        return False

    def _get_order_description(self):
        self.ensure_one()
        return self.env[self.order_model].browse(self.order_id).display_name
