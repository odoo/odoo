from odoo import _, api, models

# What a move or move line holds of the goods and quantities of a transport document (DL 147/2003
# art. 4(2)(d)): frozen once the transfer is issued (Despacho 8632/2014 1.11).
L10N_PT_ISSUED_MOVE_FIELDS = {'product_id', 'product_uom_qty', 'quantity', 'product_uom', 'picking_id'}
L10N_PT_ISSUED_MOVE_LINE_FIELDS = {'product_id', 'quantity', 'product_uom_id', 'move_id', 'picking_id'}


class StockMove(models.Model):
    _inherit = 'stock.move'

    @api.model_create_multi
    def create(self, vals_list):
        self.env['stock.picking'].browse(
            vals['picking_id'] for vals in vals_list if vals.get('picking_id')
        )._l10n_pt_raise_if_issued(_("goods"))
        return super().create(vals_list)

    def write(self, vals):
        if changed := L10N_PT_ISSUED_MOVE_FIELDS & vals.keys():
            pickings = self.picking_id | self.env['stock.picking'].browse(vals.get('picking_id'))
            pickings._l10n_pt_raise_if_issued(", ".join(self._fields[f].string for f in sorted(changed)))
        return super().write(vals)


class StockMoveLine(models.Model):
    _inherit = 'stock.move.line'

    @api.model_create_multi
    def create(self, vals_list):
        pickings = self.env['stock.picking'].browse(vals['picking_id'] for vals in vals_list if vals.get('picking_id'))
        moves = self.env['stock.move'].browse(vals['move_id'] for vals in vals_list if vals.get('move_id'))
        (pickings | moves.picking_id)._l10n_pt_raise_if_issued(_("goods"))
        return super().create(vals_list)

    def write(self, vals):
        if changed := L10N_PT_ISSUED_MOVE_LINE_FIELDS & vals.keys():
            pickings = (
                self.picking_id
                | self.env['stock.picking'].browse(vals.get('picking_id'))
                | self.env['stock.move'].browse(vals.get('move_id')).picking_id
            )
            pickings._l10n_pt_raise_if_issued(", ".join(self._fields[f].string for f in sorted(changed)))
        return super().write(vals)
