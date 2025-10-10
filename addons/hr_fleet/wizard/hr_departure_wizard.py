# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class HrDepartureWizard(models.TransientModel):
    _inherit = 'hr.departure.wizard'

    do_unassign_company_car = fields.Boolean(
        string="Release Company Car",
        default=lambda self: self.env.user.has_group('fleet.fleet_group_user'),
    )
