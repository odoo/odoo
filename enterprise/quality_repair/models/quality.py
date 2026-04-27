# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _
from odoo.exceptions import UserError


class QualityPoint(models.Model):
    _inherit = "quality.point"

    @api.constrains('measure_on', 'picking_type_ids')
    def _check_picking_type_code(self):
        for point in self:
            if point.measure_on == 'move_line' and any(picking_type.code == 'repair_operation' for picking_type in point.picking_type_ids):
                raise UserError(_("The Quantity quality check type is not possible with repair operation types."))


class QualityCheck(models.Model):
    _inherit = "quality.check"

    repair_id = fields.Many2one('repair.order', 'Repair Order', check_company=True)


class QualityAlert(models.Model):
    _inherit = "quality.alert"

    repair_id = fields.Many2one('repair.order', "Repair Order", check_company=True)
