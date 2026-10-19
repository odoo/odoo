# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class IrAccess(models.AbstractModel):
    _name = 'ir.access'
    _inherit = ['ir.access', 'mail.thread']

    active = fields.Boolean(tracking=True)
    domain = fields.Char(tracking=True)
    operation = fields.Selection(tracking=True)
