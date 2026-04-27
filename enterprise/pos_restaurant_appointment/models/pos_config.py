# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class PosConfig(models.Model):
    _inherit = 'pos.config'

    appointment_type_id = fields.Many2one('appointment.type', string='Appointment Type')
