from odoo import fields, models


class PosOrder(models.Model):
    _inherit = "pos.order"

    l10n_sa_invoice_qr_code_str = fields.Char(related="account_move.l10n_sa_qr_code_str", string="ZATCA QR Code")
    l10n_sa_invoice_edi_state = fields.Selection(related="account_move.edi_state", string="Electronic invoicing")

    def _generate_pos_order_invoice(self):
        # When generate_pdf=False (set by the SA ZATCA POS UI to avoid blocking checkout
        # on wkhtmltopdf), super() skips _generate_and_send entirely — including ZATCA.
        # We restore ZATCA EDI processing here since it is legally required to run synchronously.
        # PDF is left for on-demand generation when the invoice is first viewed or downloaded.
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
