from odoo import api, fields, models


class AccountMove(models.Model):
    _inherit = 'account.move'

    l10n_tr_edi_edispatch_ids = fields.Many2many(
        'stock.picking',
        string='e-Dispatch Orders',
        copy=False,
    )

    l10n_tr_edi_company_einvoice_status = fields.Selection(
        string="Company GİB Status",
        related='company_id.partner_id.l10n_tr_edi_customer_status',
    )
    l10n_tr_edi_dispatch_enabled = fields.Boolean(compute='_compute_l10n_tr_edi_dispatch_enabled')

    @api.depends('company_id.l10n_tr_edi_provider')
    def _compute_l10n_tr_edi_dispatch_enabled(self):
        for move in self:
            move.l10n_tr_edi_dispatch_enabled = bool(move.company_id) and move.company_id._l10n_tr_edi_dispatch_enabled()

    def _l10n_tr_edi_prefill_edispatch_ids(self):
        for move in self:
            if (
                move.move_type != 'out_invoice'
                or move.country_code != "TR"
                or move.l10n_tr_edi_company_einvoice_status != 'einvoice'
                or not move.invoice_line_ids._fields.get("sale_line_ids")
            ):
                continue
            if pickings := move.invoice_line_ids.sale_line_ids.order_id.picking_ids.filtered(
                    lambda p: p.l10n_tr_edi_send_status == "succeed"
                    and p.state == "done"
                    and p.picking_type_code == "outgoing"
                    and p.partner_id == move.partner_id,
            ):
                move.l10n_tr_edi_edispatch_ids = pickings

    @api.model_create_multi
    def create(self, vals_list):
        moves = super().create(vals_list)
        moves._l10n_tr_edi_prefill_edispatch_ids()
        return moves

    def _l10n_tr_edi_get_related_pickings(self):
        if not self.invoice_line_ids._fields.get("sale_line_ids"):
            return False
        return self.invoice_line_ids.sale_line_ids.order_id.picking_ids

    def _l10n_tr_edi_has_unlinked_dispatches(self):
        return (
            self._l10n_tr_edi_get_related_pickings()
            and self.l10n_tr_edi_customer_status in {'earchive', 'einvoice'}
            and not self.l10n_tr_edi_edispatch_ids
        )

    def _l10n_tr_edi_has_earchive_despatch_moves(self):
        pickings = self._l10n_tr_edi_get_related_pickings()
        return self.l10n_tr_edi_customer_status == 'earchive' and pickings and any(p.l10n_tr_edi_dispatch_type == 'IS_DESPATCH' for p in pickings)
