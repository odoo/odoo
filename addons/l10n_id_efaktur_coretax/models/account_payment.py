from odoo import _, fields, models
from odoo.exceptions import UserError, ValidationError, RedirectWarning


class AccountPayment(models.Model):
    _inherit = 'account.payment'

    l10n_id_ebupot_doctype = fields.Selection(selection=[
        ('N/A', 'N/A'),
        ('Imprest', 'Imprest'),
        ('Direct', 'Direct')],
        default='N/A',
        string="GovTreasurerOpt",
    )
    l10n_id_ebupot_sp2dnum = fields.Char(string="SP2DNumber")
    l10n_id_ebupot_document_xml = fields.Many2one('l10n_id_efaktur_coretax.ebupot.document', readonly=True, copy=False, string="E-Bupot Document (Coretax)")

    def _l10n_id_ebupot_build_payment_vals(self, vals):
        timezone = self.env.context.get('tz') or self.env.user.partner_id.tz or 'UTC'
        self_tz = self.with_context(tz=timezone)

        date = fields.Date.to_date(self.date)
        withholding_date = fields.Datetime.context_timestamp(
            self_tz, self.create_date
        ).date()

        vals.update({
            'TaxPeriodMonth': str(date.month),
            'TaxPeriodYear': str(date.year),
            'CounterpartTin': self.partner_id.vat,
            'IDPlaceOfBusinessActivityOfIncomeRecipient': self.partner_id.vat + (self.partner_id.l10n_id_tku or '000000'),
            'IDPlaceOfBusinessActivity': self.company_id.partner_id.vat + (self.company_id.partner_id.l10n_id_tku or '000000'),
            'GovTreasurerOpt': self.l10n_id_ebupot_doctype or 'N/A',
            'SP2DNumber': self.l10n_id_ebupot_sp2dnum,
            'WithholdingDate': withholding_date.strftime('%Y-%m-%d'),
        })

    def download_ebupot(self):
        """
        Collects data needed for ebupot and generate the xml file.
        """
        # Pre-download checks
        if len(self.company_id) > 1:
            raise UserError(_("You are not allowed to generate e-Faktur document from invoices coming from different companies"))

        err_messages = []

        if not self.company_id.vat:
            err_messages.append(_("Your company's VAT hasn't been configured yet"))
        if self.company_id.country_id.code != 'ID':
            err_messages.append(_("Your company's is not located in Indonesia"))

        # check for every partner
        for partner in self.partner_id:
            if not partner.vat:
                err_messages.append(_("VAT for customer %s hasn't been filled in yet", partner.name))
            if not partner.country_id:
                err_messages.append(_("No country is set for customer %s", partner.name))

        if not self.reconciled_bill_ids:
            err_messages.append(_("No vendor bills linked to this payment."))
        for record in self.reconciled_bill_ids:
            ChartTemplate = self.env['account.chart.template'].with_company(self.company_id)
            pph_tax_groups = {
                ChartTemplate.ref('l10n_id_tax_group_pph22', raise_if_not_found=False),
                ChartTemplate.ref('l10n_id_tax_group_pph23', raise_if_not_found=False),
                ChartTemplate.ref('l10n_id_tax_group_pph42', raise_if_not_found=False),
            }
            if not record.line_ids.tax_ids.filtered(lambda tax: tax.tax_group_id in pph_tax_groups):
                err_messages.append(_("Bill %s does not contain any PPH taxes", record.name))

        if err_messages:
            err_messages = [_('Unable to download E-Bupot for the following reason(s):')] + err_messages
            raise ValidationError('\n - '.join(err_messages))

        # All bills in self have no documents; we can create a new one for them.
        # Or all bills in self have a document, but it's the same one. Special use case but we allow downloading it.
        if not self.l10n_id_ebupot_document_xml:
            self.l10n_id_ebupot_document_xml = self.env['l10n_id_efaktur_coretax.ebupot.document'].create({
                'payment_ids': self.ids,
                'company_id': self.company_id.id,
            })
            self.l10n_id_ebupot_document_xml._generate_xml()

        # If there is more than one document, or all invoices for a document were not selected, the resulting file could cause mistakes;
        # They could get a file with additional invoices for example. In this case, we redirect them to the document view to make it clearer.
        elif len(self.l10n_id_ebupot_document_xml) > 1 or set(self.l10n_id_ebupot_document_xml.payment_ids.ids) != set(self.ids):
            action_error = {
                'name': _('Document Mismatch'),
                'view_mode': 'list',
                'res_model': 'l10n_id_efaktur_coretax.ebupot.document',
                'type': 'ir.actions.act_window',
                'views': [[False, 'list'], [False, 'form']],
                'domain': [('id', 'in', self.l10n_id_ebupot_document_xml.ids)],
            }
            msg = _("The selected invoices are partially part of one or more E-Bupot documents.\n"
                    "Please download them from the E-Bupot documents directly.")
            raise RedirectWarning(msg, action_error, _("Display Related Documents"))

        return self.download_xml()

    def download_xml(self):
        return self.l10n_id_ebupot_document_xml.action_download()

    def prepare_ebupot_vals(self):
        bills = self.reconciled_bill_ids
        ChartTemplate = self.env['account.chart.template'].with_company(self.company_id)
        pph_tax_groups = {
            ChartTemplate.ref('l10n_id_tax_group_pph22', raise_if_not_found=False),
            ChartTemplate.ref('l10n_id_tax_group_pph23', raise_if_not_found=False),
            ChartTemplate.ref('l10n_id_tax_group_pph42', raise_if_not_found=False),
        }
        ebupot_vals = []
        for bill in bills:
            payments = bill.reconciled_payment_ids.filtered(lambda p: p in self)
            bill_total = abs(bill.amount_total)
            if not bill_total:
                continue
            for payment in payments:
                payment_amount = abs(payment.amount)
                ratio = payment_amount / bill_total
                for line in bill.invoice_line_ids:
                    pph_taxes = line.tax_ids.filtered(lambda t: t.tax_group_id in pph_tax_groups)
                    if len(pph_taxes) > 1:
                        raise UserError(_(
                            "Invoice %(bill)s line '%(line)s' has more than one PPh tax.",
                            bill=bill.name,
                            line=line.name,
                        ))
                    if not pph_taxes:
                        continue

                    allocated_base = self.currency_id.round(line.price_total * ratio)
                    vals = {}
                    payment._l10n_id_ebupot_build_payment_vals(vals)
                    bill._l10n_id_ebupot_build_invoice_vals(vals)
                    line._l10n_id_ebupot_build_invoice_line_vals(
                        vals,
                        allocated_base=allocated_base,
                    )
                    ebupot_vals.append(vals)
        if not ebupot_vals:
            raise UserError(_("No PPh data found to generate E-Bupot."))
        return ebupot_vals
