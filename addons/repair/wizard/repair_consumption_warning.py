from odoo import fields, models


class RepairConsumptionWarning(models.TransientModel):
    _name = 'repair.consumption.warning'
    _description = "Wizard for warning about mismatching expected vs actual component consumption quantities for ROs"

    repair_id = fields.Many2one('repair.order')
    repair_consumption_warning_line_ids = fields.One2many('repair.consumption.warning.line', 'repair_consumption_warning_id')

    def action_confirm(self):
        return self.repair_id.action_repair_done()

    def action_set_qty(self):
        existing_moves_lines = self.repair_consumption_warning_line_ids.filtered('move_id')
        for line in existing_moves_lines:
            line.move_id.quantity = line.product_expected_qty_uom
        self.env['stock.move'].create([{
            'product_id': line.product_id.id,
            'uom_id': (line.uom_id or line.product_id.uom_id).id,
            'product_uom_qty': line.product_expected_qty_uom,
            'quantity': line.product_expected_qty_uom,
            'repair_id': self.repair_id.id,
        } for line in self.repair_consumption_warning_line_ids - existing_moves_lines])
        return self.action_confirm()

    def action_cancel(self):
        return


class RepairConsumptionWarningLine(models.TransientModel):
    _name = 'repair.consumption.warning.line'
    _description = "Line of issue consumption"

    repair_consumption_warning_id = fields.Many2one('repair.consumption.warning', "Parent Wizard", readonly=True, required=True, ondelete="cascade")
    product_id = fields.Many2one('product.product', "Product", readonly=True, required=True)
    uom_id = fields.Many2one('uom.uom', "Unit", readonly=True)
    product_consumed_qty_uom = fields.Float("Consumed", readonly=True)
    product_expected_qty_uom = fields.Float("To Consume", readonly=True)
    move_id = fields.Many2one('stock.move', readonly=True)
