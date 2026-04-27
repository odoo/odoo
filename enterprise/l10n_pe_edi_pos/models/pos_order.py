from odoo import _, models, fields
from odoo.addons.l10n_pe_edi.models.account_move import REFUND_REASON
from odoo.exceptions import UserError


class PosOrder(models.Model):
    _inherit = 'pos.order'

    l10n_pe_edi_refund_reason = fields.Selection(
        selection=REFUND_REASON,
        string="Credit Reason",
        help="It contains all possible values for the refund reason according to Catalog No. 09",
    )

    # -------------------------------------------------------------------------
    # OVERRIDES
    # -------------------------------------------------------------------------

    def action_pos_order_invoice(self):
        # EXTENDS 'point_of_sale'
        if self.country_code == 'PE' and self.refunded_order_id and not self.refunded_order_id.account_move:
            raise UserError(_("You cannot invoice this refund since the related order is not invoiced yet."))
        return super().action_pos_order_invoice()

    def _prepare_invoice_vals(self):
        # EXTENDS 'point_of_sale'
        vals = super()._prepare_invoice_vals()
        if self.country_code == 'PE':
            refunded_move = self.refunded_order_id.account_move
            if len(refunded_move) > 1:
                raise UserError(_("You cannot refund several invoices at once."))
            if refunded_move:
                vals['l10n_pe_edi_refund_reason'] = self.l10n_pe_edi_refund_reason
                refunded_invoice_code = refunded_move.l10n_latam_document_type_id.code
                if refunded_invoice_code == '01':
                    # refunding a "Factura electrónica" is done through a "Nota de Crédito electrónica"
                    vals['l10n_latam_document_type_id'] = self.env.ref('l10n_pe.document_type07').id
                elif refunded_invoice_code == '03':
                    # refunding a "Boleta de venta electrónica" is done through a "Nota de Crédito Boleta electrónica"
                    vals['l10n_latam_document_type_id'] = self.env.ref('l10n_pe.document_type07b').id
        return vals

    def _generate_pos_order_invoice(self):
        """ We can skip the accout_edi cron because it will be trigerred manually in l10n_pe_edi_pos/models/account_move.py _post() """
        if 'pe_ubl_2_1' in self.config_id.invoice_journal_id.edi_format_ids.mapped('code'):
            return super(PosOrder, self.with_context(skip_account_edi_cron_trigger=True))._generate_pos_order_invoice()
        else:
            return super()._generate_pos_order_invoice()
