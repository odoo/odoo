from odoo import api, models, _
from odoo.exceptions import UserError

class ResourceResource(models.Model):
    _inherit = "resource.resource"

    @api.constrains('calendar_id')
    def _check_resource_calendar(self):
        if workcenters := self.env['mrp.workcenter'].search([
            ('resource_id', 'in', self.ids), ('resource_calendar_id', '=', False)
        ]):
            raise UserError(_(
                "You cannot remove Working Time because it is used in the work center(s): '%s'.", workcenters.mapped("name"))
            )
