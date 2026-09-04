from odoo import fields, models


class AccountMove(models.Model):
    _inherit = 'account.move'

    l10n_tr_nilvera_edispatch_ids = fields.Many2many(
        'stock.picking',
        string='e-Dispatch Orders',
        copy=False,
    )

    l10n_tr_nilvera_company_einvoice_status = fields.Selection(
        string="Company Nilvera Status",
        related='company_id.partner_id.l10n_tr_nilvera_customer_status',
    )

    def _prefill_l10n_tr_nilvera_edispatch_ids(self):
        for move in self:
            if (
                move.move_type != 'out_invoice'
                or move.country_code != "TR"
                or move.l10n_tr_nilvera_company_einvoice_status != 'einvoice'
                or not move.invoice_line_ids._fields.get("sale_line_ids")
            ):
                continue
            move.l10n_tr_nilvera_edispatch_ids = move.invoice_line_ids.sale_line_ids.order_id.picking_ids.filtered(
                    lambda p: p.l10n_tr_nilvera_send_status == "succeed"
                    and p.state == "done"
                    and p.picking_type_code == "outgoing"
                    and p.partner_id == move.partner_id,
                ).ids

    def create(self, vals_list):
        moves = super().create(vals_list)
        moves._prefill_l10n_tr_nilvera_edispatch_ids()
        return moves

    def _get_related_pickings(self):
        if not self.invoice_line_ids._fields.get("sale_line_ids"):
            return False
        return self.invoice_line_ids.sale_line_ids.order_id.picking_ids

    def _has_unlinked_dispatches(self):
        return (
            self._get_related_pickings()
            and self.l10n_tr_nilvera_customer_status in ['earchive', 'einvoice']
            and not self.l10n_tr_nilvera_edispatch_ids
        )

    def _has_earchive_despatch_moves(self):
        pickings = self._get_related_pickings()
        return self.l10n_tr_nilvera_customer_status == 'earchive' and any(p.l10n_tr_nilvera_dispatch_type == 'IS_DESPATCH' for p in pickings)
