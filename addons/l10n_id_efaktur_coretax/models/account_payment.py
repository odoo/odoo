# Part of Odoo. See LICENSE file for full copyright and licensing details.

from collections import defaultdict

from odoo import _, fields, models
from odoo.exceptions import UserError, ValidationError, RedirectWarning
from odoo.tools.float_utils import float_repr

GOV_TREASURER_OPT = [
    ('N/A', 'N/A'),
    ('Imprest', 'Imprest'),
    ('Direct', 'Direct'),
]

EBUPOT_DOCUMENT_TYPE = [
    ('Announcement', 'Announcement - Pengumuman'),
    ('CommercialInvoice', 'CommercialInvoice - Surat Tagihan'),
    ('Contract', 'Contract - Kontrak'),
    ('CurrentAccount', 'CurrentAccount - Jasa Giro'),
    ('Decree', 'Decree - Decree'),
    ('DeedOfEngagement', 'DeedOfEngagement - Akta Perjanjian'),
    ('DeedOfGeneral', 'DeedOfGeneral - Akta RUPS'),
    ('Other', 'Other - Lainnya'),
    ('OtherFacilityDoc', 'OtherFacilityDoc - Dokumen Fasilitas Lainnya'),
    ('PaymentProof', 'PaymentProof - Bukti Pembayaran'),
    ('StatementLetter', 'StatementLetter - Surat Pernyataan'),
    ('TaxInvoice', 'TaxInvoice - Faktur Pajak'),
    ('TaxRegulationDoc', 'TaxRegulationDoc - Dokumen Perpajakan'),
    ('TradeConfirmation', 'TradeConfirmation - Trade Confirmation'),
]


class AccountPayment(models.Model):
    _inherit = 'account.payment'

    l10n_id_ebupot_gov_treasurer_opt = fields.Selection(
        selection=GOV_TREASURER_OPT,
        string="Payment Option",
        help="Payment method (only used by government institution withholders/collectors)",
    )
    l10n_id_ebupot_sp2d_number = fields.Char(string="SP2D Number")
    l10n_id_ebupot_document_type = fields.Selection(
        selection=EBUPOT_DOCUMENT_TYPE,
        default='TaxInvoice',
        string="Document Type",
        help="Filled with the type of document that serves as the basis for withholding/collection",
    )
    l10n_id_ebupot_document_number = fields.Char(
        string="Document Number",
        help="Filled in with the number of the basic document for cutting/collection",
    )
    l10n_id_ebupot_document_date = fields.Date(
        string="Document Date",
        help="Filled with the date of the basic document for withholding/collection",
    )
    l10n_id_coretax_document = fields.Many2one('l10n_id_efaktur_coretax.document', readonly=True, copy=False, string="Coretax Document")

    # ----------------
    # Business methods
    # ----------------

    def _l10n_id_ebupot_payment_vals(self):
        """ The part of a Bpu record that comes from the payment (period, counterpart and document). """
        self.ensure_one()
        partner = self.partner_id.commercial_partner_id
        company_partner = self.company_id.partner_id
        return {
            'TaxPeriodMonth': str(self.date.month),
            'TaxPeriodYear': str(self.date.year),
            'CounterpartTin': partner.vat,
            'IDPlaceOfBusinessActivityOfIncomeRecipient': partner.vat + partner._l10n_id_efaktur_tku_branch(),
            'IDPlaceOfBusinessActivity': self.company_id.vat + company_partner._l10n_id_efaktur_tku_branch(),
            'GovTreasurerOpt': self.l10n_id_ebupot_gov_treasurer_opt or 'N/A',
            'SP2DNumber': self.l10n_id_ebupot_sp2d_number,
            'WithholdingDate': self.date.strftime('%Y-%m-%d'),  # Date the withholding happens (the payment date)
            'Document': self.l10n_id_ebupot_document_type or 'TaxInvoice',
            'DocumentNumber': self.l10n_id_ebupot_document_number,
            'DocumentDate': self.l10n_id_ebupot_document_date and self.l10n_id_ebupot_document_date.strftime('%Y-%m-%d'),
        }

    def _l10n_id_ebupot_get_bpu_lines(self):
        self.ensure_one()
        company_currency = self.company_currency_id
        bpu_lines = []
        for line in self.withholding_line_ids:
            origin = line.source_tax_id or line.tax_id
            bpu_lines.append({
                'object_code': origin.l10n_id_ebupot_code.code,
                'facility': line.tax_id.l10n_id_ebupot_facility or 'N/A',
                'rate': abs(line.tax_id.amount),
                'base_amount': self.currency_id._convert(line.base_amount, company_currency, self.company_id, self.date),
            })
        return bpu_lines

    def _l10n_id_ebupot_check_payments(self):
        err_messages = []
        for company in self.company_id:
            if not company.vat:
                err_messages.append(_("Your company's NPWP hasn't been configured yet"))
            if company.account_fiscal_country_id.code != 'ID':
                err_messages.append(_("Your company is not located in Indonesia"))

        for payment in self:
            partner = payment.partner_id.commercial_partner_id
            if not partner.vat:
                err_messages.append(_("NPWP/NIK for partner %s hasn't been filled in yet", partner.name))

            if payment.payment_type != 'outbound':
                err_messages.append(_("Payment %s is not a vendor payment. E-Bupot can only be issued for the PPh you withhold.", payment.display_name))
            if payment.withhold == 'payment' or not payment.withholding_line_ids:
                err_messages.append(_("Payment %s does not withhold any PPh", payment.display_name))

            for line in payment.withholding_line_ids:
                origin = line.source_tax_id or line.tax_id
                if not origin.l10n_id_ebupot_code:
                    err_messages.append(_(
                        "Tax %(tax)s has no E-Bupot object code; set its Origin Tax on payment %(payment)s.",
                        tax=line.tax_id.display_name, payment=payment.display_name,
                    ))

            if payment.withholding_line_ids and not payment.l10n_id_ebupot_document_number:
                err_messages.append(_("Payment %s has no E-Bupot document number", payment.display_name))
            if payment.withholding_line_ids and not payment.l10n_id_ebupot_document_date:
                err_messages.append(_("Payment %s has no E-Bupot document date", payment.display_name))

        if err_messages:
            raise ValidationError(_('Unable to download E-Bupot for the following reason(s):\n%(reasons)s', reasons='\n - '.join(err_messages)))

    def _l10n_id_ebupot_prepare_vals(self):
        """ Build the Bpu records of every payment in self, grouped by the month they are reported in. """
        self._l10n_id_ebupot_check_payments()

        grouped_data = defaultdict(list)
        for payment in self:
            payment_vals = payment._l10n_id_ebupot_payment_vals()
            for bpu_line in payment._l10n_id_ebupot_get_bpu_lines():
                grouped_data[payment.date.strftime('%Y-%m')].append({
                    **payment_vals,
                    'TaxCertificate': bpu_line['facility'],
                    'TaxObjectCode': bpu_line['object_code'],
                    'TaxBase': float_repr(bpu_line['base_amount'], precision_digits=payment.company_currency_id.decimal_places),
                    'Rate': bpu_line['rate'],
                })

        if not grouped_data:
            raise UserError(_("No PPh data found to generate E-Bupot."))

        return [
            {'payment_month': payment_month, 'data': vals_list}
            for payment_month, vals_list in grouped_data.items()
        ]

    def download_ebupot(self):
        """ Gather the payments into an E-Bupot document and download it. """
        if len(self.company_id) > 1:
            raise UserError(_("You are not allowed to generate an E-Bupot document from payments coming from different companies"))

        if not self.l10n_id_coretax_document:
            self.l10n_id_coretax_document = self.env['l10n_id_efaktur_coretax.document'].create({
                'document_type': 'ebupot',
                'payment_ids': [fields.Command.set(self.ids)],
                'company_id': self.company_id.id,
            })
            self.l10n_id_coretax_document._generate_xml()

        elif len(self.l10n_id_coretax_document) > 1 or set(self.l10n_id_coretax_document.payment_ids.ids) != set(self.ids):
            action_error = {
                'name': _('Document Mismatch'),
                'view_mode': 'list',
                'res_model': 'l10n_id_efaktur_coretax.document',
                'type': 'ir.actions.act_window',
                'views': [[False, 'list'], [False, 'form']],
                'domain': [('id', 'in', self.l10n_id_coretax_document.ids)],
            }
            msg = _("The selected payments are partially part of one or more E-Bupot documents.\n"
                    "Please download them from the E-Bupot documents directly.")
            raise RedirectWarning(msg, action_error, _("Display Related Documents"))

        return self.l10n_id_coretax_document.action_download()

    def action_open_coretax_document(self):
        self.ensure_one()
        return self.l10n_id_coretax_document._get_records_action()
