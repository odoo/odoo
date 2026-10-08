from odoo import models


class AccountEdiCommon(models.AbstractModel):
    _inherit = 'account.edi.common'

    def _get_line_trade_references(self, vals, base_line):
        # EXTENDS account_edi_ubl_cii
        references = super()._get_line_trade_references(vals, base_line)
        line = base_line['record']
        if not isinstance(line, models.BaseModel) or line._name != 'account.move.line':
            return references

        sale_lines = line.sale_line_ids
        if len(sale_lines) == 1:
            moves = sale_lines.move_ids.filtered(lambda m: m.state == 'done' and m.location_dest_id.usage == 'customer')
            # A line can only refer to a single delivery order: none if the line was shipped in several ones
            # (e.g. a backorder), rather than a wrong one.
            if len(moves) == 1 and moves.picking_id:
                picking = moves.picking_id
                references['despatch_ref'] = picking.name
                references['despatch_line_ref'] = str(picking.move_ids.ids.index(moves.id) + 1)
        return references
