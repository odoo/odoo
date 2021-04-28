# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class PaymentIcon(models.Model):
    _name = 'payment.icon'
    _description = 'Payment Icon'
    _order = 'sequence, name'

    name = fields.Char(string="Name")
    acquirer_ids = fields.Many2many(
        string="Acquirers", comodel_name='payment.acquirer',
        help="The list of acquirers supporting this payment icon")
    image = fields.Image(
        string="Image", max_width=64, max_height=64,
        help="This field holds the image used for this payment icon, limited to 64x64 px")
    image_payment_form = fields.Image(
        string="Image displayed on the payment form", related='image', store=True, max_width=45,
        max_height=30)
    sequence = fields.Integer('Sequence', default=1)
