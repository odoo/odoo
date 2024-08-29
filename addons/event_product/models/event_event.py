from odoo import fields, models
from odoo.addons import event


class EventEvent(models.Model, event.EventEvent):

    currency_id = fields.Many2one(
        'res.currency', string='Currency',
        related='company_id.currency_id', readonly=True)
