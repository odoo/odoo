# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import api, models


class QualityCheckWizard(models.TransientModel):
    _inherit = 'quality.check.wizard'

    @api.onchange('qty_failed')
    def onchange_qty_failed(self):
        mo = self.check_ids.production_id
        if mo and mo.product_id == self.check_ids.product_id:
            self.qty_failed = self.qty_line

    def do_fail(self):
        check = self.current_check_id
        if check.production_id and check.point_id.measure_on == 'move_line':
            check.move_line_id = check.production_id.finished_move_line_ids.filtered(
                lambda ml: ml.product_id == self.product_id
            )[:1]
            check.lot_line_id = check.production_id.lot_producing_id
        return super().do_fail()
