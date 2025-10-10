# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class HrVersion(models.Model):
    _inherit = 'hr.version'

    departure_do_unassign_equipment = fields.Boolean(related='departure_id.do_unassign_equipment')
