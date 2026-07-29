# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import Command, api, fields, models

from odoo.addons.web.controllers.utils import clean_action


class StockPickingType(models.Model):
    _inherit = "stock.picking.type"

    auto_print_cmr_report = fields.Boolean(
        'Auto Print Consignment Note (CMR)',
        help="If this checkbox is ticked, Odoo will automatically print the Consignment Note (CMR) of a delivery when it is validated.",
    )
    dispatch_management = fields.Boolean(
        'Dispatch Management',
        help="Enable this option to display dispatch management related details in the batch/wave form view and operations kanban overview."
    )
    dock_ids = fields.Many2many(
        'stock.location',
        'dock_location_stock_picking_type_rel',
        domain="[('warehouse_id', '=', warehouse_id), ('usage', '=', 'internal')]",
        compute='_compute_dock_ids', store=True, readonly=False
    )

    @api.depends('warehouse_id')
    def _compute_dock_ids(self):
        for picking_type in self:
            if picking_type.warehouse_id != picking_type._origin.warehouse_id and picking_type.dock_ids:
                picking_type.dock_ids = [Command.clear()]


class StockPicking(models.Model):
    _inherit = "stock.picking"

    zip = fields.Char(related='partner_id.zip', string='Zip', search="_search_zip")

    def _search_zip(self, operator, value):
        return [('partner_id.zip', operator, value)]

    def write(self, vals):
        res = super().write(vals)
        if 'batch_id' not in vals:
            return res
        batch = self.env['stock.picking.batch'].browse(vals.get('batch_id'))
        if batch and batch.dock_id:
            batch._set_moves_destination_to_dock()
        else:
            self._reset_location()
        return res

    def _reset_location(self):
        for picking in self:
            moves = picking.move_ids.filtered(lambda m: not m.location_dest_id._child_of(picking.location_dest_id))
            moves.write({'location_dest_id': picking.location_dest_id.id})

    def _get_autoprint_report_actions(self):
        report_actions = []
        if pickings_to_print_cmr := self.filtered(
            lambda p: p.picking_type_code == 'outgoing' and p.picking_type_id.auto_print_cmr_report
        ):
            if batch_id := self.env.context.get('batches_to_validate'):
                report = 'stock_fleet.action_report_cmr_batch'
            else:
                report = 'stock_fleet.action_report_cmr'
            action = self.env.ref(report).report_action(batch_id or pickings_to_print_cmr.ids, config=False)
            clean_action(action, self.env)
            report_actions.append(action)
        return report_actions + super()._get_autoprint_report_actions()
