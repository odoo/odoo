from lxml import etree
from odoo import models, fields, _
from odoo.exceptions import UserError


class AccountJournal(models.Model):
    _inherit = 'account.journal'

    is_self_billing = fields.Boolean(
        string='Self Billing',
        help="This journal is for self-billing invoices. "
             "If the company has activated self-billing sending on Peppol, "
             "vendor bills will be available to be sent as self-billed invoices via Peppol.",
    )

    def _is_self_billing_invoice(self, xml_raw):
        if not xml_raw:
            return False
        try:
            tree = etree.fromstring(xml_raw)
        except Exception:  # noqa: BLE001
            return False

        invoice_type_code = tree.findtext('.//{*}InvoiceTypeCode')
        credit_note_type_code = tree.findtext('.//{*}CreditNoteTypeCode')
        return invoice_type_code in ['389', '527'] or credit_note_type_code == '261'

    def _deduce_special_journal_from_attachment(self, attachment, move_type):
        # OVERRIDE 'account'
        if (
            not attachment
            or not self._is_self_billing_invoice(attachment.raw)
            or move_type not in self.env['account.move'].get_sale_types(include_receipts=True)
        ):
            return None

        journal = self.env['account.journal'].search([
            *self.env['account.journal']._check_company_domain(self.env.company),
            ('type', '=', 'sale'),
            ('is_self_billing', '=', True),
        ], limit=1)
        if not journal:
            raise UserError(_("No self-billing journal was found."))
        return journal
