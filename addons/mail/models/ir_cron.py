# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class IrCron(models.AbstractModel):
    _name = 'ir.cron'
    _inherit = ['ir.cron', 'mail.thread', 'mail.activity.mixin']

    user_id = fields.Many2one(tracking=True)
    interval_number = fields.Integer(tracking=True)
    interval_type = fields.Selection(tracking=True)
    priority = fields.Integer(tracking=True)
    active = fields.Boolean(tracking=True)
