from odoo import api, fields, models


class PosOrder(models.Model):
    _inherit = "pos.order"

    l10n_sa_invoice_qr_code_str = fields.Char(related="account_move.l10n_sa_qr_code_str", string="ZATCA QR Code")
    l10n_sa_invoice_edi_state = fields.Selection(related="account_move.edi_state", string="Electronic invoicing")

    @api.model
    def create_from_ui(self, orders, draft=False):
        """ The frontend does not reload the ``pos.order`` records after syncing them, so the
            QR code of the freshly created invoice travels back with the sync response for the
            receipt to display the Phase 2 QR code.
        """
        res = super().create_from_ui(orders, draft)
        if self.env.company.country_id.code == 'SA':
            # The QR code is computed from the EDI document and its attachment, which the
            # cashier cannot read; only the QR code of each order's own invoice is exposed.
            orders_sudo = self.sudo().browse([order_data['id'] for order_data in res])
            for order_data, order_sudo in zip(res, orders_sudo):
                order_data['l10n_sa_invoice_qr_code_str'] = order_sudo.l10n_sa_invoice_qr_code_str
        return res

    def _export_for_ui(self, order):
        """ Same as ``create_from_ui``, but for orders loaded back in the frontend, so that
            reprinting the receipt of a past order also shows the Phase 2 QR code.
        """
        res = super()._export_for_ui(order)
        if order.company_id.country_id.code == 'SA':
            res['l10n_sa_invoice_qr_code_str'] = order.sudo().l10n_sa_invoice_qr_code_str
        return res

    def _generate_pos_order_invoice(self):
        # Submit the invoice to ZATCA now instead of leaving it to the EDI cron, so that the
        # receipt printed right after checkout carries the Phase 2 QR code. The PDF is not
        # generated here (generate_pdf=False) as it would predate the clearance and lack the QR
        # code; it is generated on demand when the invoice is downloaded.
        if self.env.context.get('generate_pdf', True) or self.company_id.country_id.code != 'SA':
            return super()._generate_pos_order_invoice()

        orders_needing_invoice = self.filtered(lambda o: not o.account_move)
        result = super()._generate_pos_order_invoice()

        for order in orders_needing_invoice:
            if order.account_move:
                order.account_move.sudo().edi_document_ids.filtered(
                    lambda d: d.state == 'to_send' and d.edi_format_id._needs_web_services()
                )._process_documents_web_services(with_commit=False)

        return result
