from odoo import _, api, models
from odoo.exceptions import UserError
from odoo.tools import float_compare


def _l10n_pt_changed_fields(records, vals, field_names):
    """
    The fields of ``field_names`` in ``vals`` whose value would change on any of ``records``: validating
    a transfer issued beforehand writes back the quantities it was issued with, which is no change.
    """
    changed = set()
    for field_name in field_names & vals.keys():
        field = records._fields[field_name]
        for record in records:
            value = field.convert_to_record(field.convert_to_cache(vals[field_name], record), record)
            if field.type == 'float':
                digits = field.get_digits(record.env)
                if float_compare(record[field_name], value, precision_digits=digits[1] if digits else 6):
                    changed.add(field_name)
                    break
            elif record[field_name] != value:
                changed.add(field_name)
                break
    return changed

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

    def _action_cancel(self):
        # The goods of an issued transport document are cancelled only with their transfer, annulled
        # with a reason before its transport starts (`stock.picking.action_cancel`).
        issued = self.picking_id._l10n_pt_issued().filtered(lambda p: p.state not in ('done', 'cancel'))
        issued._l10n_pt_check_annullable()
        if unexplained := issued.filtered(lambda p: not p.l10n_pt_cancel_reason):
            raise UserError(_(
                "%(documents)s was issued as a transport document: cancel its transfer from its form, with "
                "the reason it is annulled.",
                documents=", ".join(unexplained.mapped('l10n_pt_document_number')),
            ))
        return super()._action_cancel()

    def write(self, vals):
        if L10N_PT_ISSUED_MOVE_FIELDS & vals.keys():
            issued = self.filtered(lambda m: m.picking_id._l10n_pt_issued())
            if changed := _l10n_pt_changed_fields(issued, vals, L10N_PT_ISSUED_MOVE_FIELDS):
                issued.picking_id._l10n_pt_raise_if_issued(", ".join(self._fields[f].string for f in sorted(changed)))
            target = self.env['stock.picking'].browse(vals.get('picking_id'))
            if target and self.filtered(lambda m: m.picking_id != target):
                target._l10n_pt_raise_if_issued(_("goods"))
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
        if L10N_PT_ISSUED_MOVE_LINE_FIELDS & vals.keys():
            issued = self.filtered(lambda l: l.picking_id._l10n_pt_issued())
            if changed := _l10n_pt_changed_fields(issued, vals, L10N_PT_ISSUED_MOVE_LINE_FIELDS):
                issued.picking_id._l10n_pt_raise_if_issued(", ".join(self._fields[f].string for f in sorted(changed)))
            target = self.env['stock.picking'].browse(vals.get('picking_id')) | self.env['stock.move'].browse(vals.get('move_id')).picking_id
            if target and self.filtered(lambda l: l.picking_id not in target):
                target._l10n_pt_raise_if_issued(_("goods"))
        return super().write(vals)
