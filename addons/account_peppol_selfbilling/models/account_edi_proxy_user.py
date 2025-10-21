from lxml import etree

from odoo import models


class AccountEdiProxyClientUser(models.Model):
    _inherit = 'account_edi_proxy_client.user'

    def _peppol_get_import_journal_and_move_type(self, attachment):
        # Self-billed invoices are invoices which your customer creates on your behalf and sends you via Peppol.
        # In this case, the invoice needs to be created as an out_invoice in a sale journal.
        xml_tree = etree.fromstring(attachment.raw)

        if xml_tree.findtext('.//{*}InvoiceTypeCode') in ['389', '527'] or xml_tree.findtext('.//{*}CreditNoteTypeCode') == '261':
            # 329/527: Self-billing invoice; 261: Self-billing credit note
            journal = self.env['account.journal'].search(
                [
                    *self.env['account.journal']._check_company_domain(self.company_id),
                    ('type', '=', 'sale'),
                ],
                limit=1,
            )
            move_type = 'out_invoice'
        else:
            journal = self.company_id.peppol_purchase_journal_id
            move_type = 'in_invoice'

        return journal, move_type
