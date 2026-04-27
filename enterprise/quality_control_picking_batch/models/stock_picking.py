# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models


class StockPickingBatch(models.Model):
    _inherit = "stock.picking"

    def _add_to_wave_post_picking_split_hook(self):
        """
        As moves might have been transfered from one picking to an other or created and assigned
        by passing the confirmation process,we need to clean the obsolete checks per product and
        to recreate checks per operation and products on the newly created pickings.
        """
        super()._add_to_wave_post_picking_split_hook()
        # clean obsolete checks
        checks_by_picking = self.check_ids.filtered(lambda qc: qc.measure_on in ('operation', 'product') and qc.quality_state == 'none').grouped('picking_id')
        checks_ids_to_unlink = set()
        for picking, checks in checks_by_picking.items():
            products = picking.move_ids.product_id
            for check in checks:
                if check.measure_on == 'operation' or (check.measure_on == 'product' and check.product_id not in products):
                    checks_ids_to_unlink.add(check.id)
        self.env['quality.check'].browse(checks_ids_to_unlink).sudo().unlink()
        # recreated product and operation checks
        self.move_ids.sudo()._create_quality_checks()
