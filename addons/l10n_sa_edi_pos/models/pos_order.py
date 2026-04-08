from odoo import fields, models


class PosOrder(models.Model):
    _inherit = "pos.order"

    l10n_sa_invoice_qr_code_str = fields.Char(related="account_move.l10n_sa_qr_code_str", string="ZATCA QR Code")
    l10n_sa_invoice_edi_state = fields.Selection(related="account_move.edi_state", string="Electronic invoicing")

<<<<<<< ab4ccaf005237ba38f9629197e85f955bf17067d
    def is_settlement_order(self):
        self.ensure_one()
        """
        Check if the invoice is linked to a POS settlement order
        Only available when pos_settle_due module is installed
        """
        if not self.env["pos.order.line"]._fields.get("settled_order_id"):
            return False
        return any(line.settled_order_id for line in self.lines)
||||||| c4ec462002e512635170fce2d9600da67f459a34
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
                order.account_move.edi_document_ids.filtered(
                    lambda d: d.state == 'to_send' and d.edi_format_id._needs_web_services()
                )._process_documents_web_services(with_commit=False)

        return result
=======
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
>>>>>>> cf27fe5e88132c69a7c6105275a1572593e40555
