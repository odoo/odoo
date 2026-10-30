from markupsafe import Markup

from odoo import fields, models


class PosOrder(models.Model):
    _inherit = "pos.order"

    country_code = fields.Char(related='company_id.account_fiscal_country_id.code')

    def _generate_pos_order_invoice(self):
        if self.country_code != 'PT':
            return super()._generate_pos_order_invoice()

        # A session can outlive its series (opened on 31 December): provide the series of each order's date.
        for config, orders in self.grouped(lambda o: o.session_id.config_id).items():
            for date in {fields.Date.context_today(order, order.date_order) for order in orders}:
                config._l10n_pt_pos_ensure_at_series(date)

        # A sale without a customer is sold to the generic final consumer, as its document says (SAF-T
        # has no customer-less document), so core's invoice, payments, reconciliation and refund
        # credit note all apply to it; `_prepare_invoice_vals` makes it a simplified invoice.
        if customerless := self.filtered(lambda o: not o.partner_id):
            customerless.partner_id = self.env.ref('l10n_pt_certification.pt_final_consumer')
        # The PoS hands the invoice out at once: it is issued when posted, before its payments are reconciled.
        return super(PosOrder, self.with_context(generate_pdf=False, l10n_pt_issue_automatically=True))._generate_pos_order_invoice()

    def _l10n_pt_is_anonymous(self):
        """Sold to nobody in particular: no customer, or the generic final consumer (NIF 999999990)."""
        final_consumer = self.env.ref('l10n_pt_certification.pt_final_consumer', raise_if_not_found=False)
        return all(not order.partner_id or order.partner_id == final_consumer for order in self)

    def _prepare_invoice_vals(self):
        vals = super()._prepare_invoice_vals()
        if self[:1].country_code == 'PT' and vals['move_type'] == 'out_invoice' and self._l10n_pt_is_anonymous():
            # An anonymous sale is a simplified invoice (FS, CIVA art. 40) within its cap. Above the
            # cap it stays an invoice-receipt (FR) to the generic final consumer: since DL 28/2019 a
            # non-taxable buyer need not be identified on an invoice, whatever the amount (CIVA art.
            # 36(5)(a)). A refund stays core's credit note against the document it refunds.
            limit = self.env['account.move']._l10n_pt_simplified_invoice_limit(self.lines)
            eur = self.env.ref('base.EUR')
            amount_eur = sum(
                order.currency_id._convert(order.amount_total, eur, order.company_id, vals['invoice_date'])
                for order in self
            )
            if amount_eur > limit:
                return vals
            vals['move_type'] = 'out_receipt'
            vals['invoice_line_ids'] = self._prepare_invoice_lines('out_receipt')
        return vals

    def update_l10n_pt_print_version(self):
        # The receipt is the print of the order's invoice (FS, FR): printed at the till or from the
        # back office, the document has one Original.
        self.ensure_one()
        # sudo: every print at the till counts, and a cashier may not write invoices.
        self.account_move.sudo()._l10n_pt_update_print_version()

    def post_reprint_reason(self, reason):
        self.ensure_one()
        msg = self.env._("Reason for reprinting document %(name)s:", name=self.name) + Markup("<br/>") + (reason or "")
        self.message_post(body=msg)
        return True

    def l10n_pt_get_order_vals(self):
        self.ensure_one()
        invoice = self.account_move
        if not invoice:
            return {}
        return {
            'name': self.name,
            'hash_short': invoice.l10n_pt_inalterable_hash_short,
            'atcud': invoice.l10n_pt_atcud,
            'document_identifier': invoice.l10n_pt_document_number,
            'qr_code_str': invoice.l10n_pt_qr_code_str,
            'is_reprint': bool(invoice.l10n_pt_print_version),
            'document_type': invoice._l10n_pt_get_document_type_designation(),
            'training_mode': invoice.l10n_pt_at_series_id.training_series if invoice.l10n_pt_at_series_id else False,
        }
