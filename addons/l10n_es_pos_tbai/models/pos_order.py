<<<<<<< HEAD
||||||| MERGE BASE
=======
from odoo import models


class PosOrder(models.Model):
    _inherit = 'pos.order'

    def get_l10n_es_pos_tbai_qrurl(self):
        """ This function manually triggers the account.edi post CRON and synchronously
        wait for the process to finish, so that we can retrieve the generated QR code
        from the post response and transfer it to JS and eventually the Order Receipt XML. """
        self.ensure_one()
        if 'es_tbai' in self.account_move.edi_document_ids.edi_format_id.mapped('code'):
            tbai_documents_to_send = self.account_move.edi_document_ids.filtered(
                lambda d: d.edi_format_id.code == 'es_tbai' and d.state == 'to_send')
            tbai_documents_to_send._process_documents_web_services(job_count=1)
            return self.account_move._get_l10n_es_tbai_qr()

    def _generate_pos_order_invoice(self):
        # OVERRIDES 'point_of_sale'
        """ We need to make sure that the account.edi CRON does not run on TicketBai Invoices,
        because we plan to manually trigger it in our custom function above so that we can
        synchronously wait for the process to finish. """
        journal = self.config_id.l10n_es_simplified_invoice_journal_id \
            if self.is_l10n_es_simplified_invoice else self.config_id.invoice_journal_id

        if 'es_tbai' in journal.edi_format_ids.mapped('code'):
            return super(PosOrder, self.with_context(skip_account_edi_cron_trigger=True))._generate_pos_order_invoice()
        else:
            return super()._generate_pos_order_invoice()

    def _process_order(self, order, draft, existing_order):
        if'l10n_es_tbai_refund_reason' in order['data']:
            return super(PosOrder, self.with_context(l10n_es_tbai_refund_reason=order['data']['l10n_es_tbai_refund_reason']))._process_order(order, draft, existing_order)
        else:
            return super()._process_order(order, draft, existing_order)

    def _prepare_invoice_vals(self):
        res = super()._prepare_invoice_vals()
        if self.env.context.get('l10n_es_tbai_refund_reason'):
            res['l10n_es_tbai_refund_reason'] = self.env.context.get('l10n_es_tbai_refund_reason')
        return res

>>>>>>> FORWARD PORTED
