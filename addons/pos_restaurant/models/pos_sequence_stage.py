# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class PosSequenceStage(models.Model):
    _name = 'pos.sequence.stage'
    _description = 'Allow the user to quickly select the sequence of the meals.'
    _order = "sequence, name"
    _inherit = ['pos.load.mixin']

    name = fields.Char('Name', required=True)
    color = fields.Integer('Color Index', default=0)
    sequence = fields.Integer(default=1)
