from odoo import _, models
from odoo.exceptions import UserError

from odoo.addons.l10n_pt_certification.const import PT_CERTIFICATION_NUMBER


class IrActionsReport(models.Model):
    _inherit = 'ir.actions.report'

    def _pre_render_qweb_pdf(self, report_ref, res_ids=None, data=None):
        if len(res_ids) > 1:
            # Check that, if multiple documents being printed, only PT companies are selected,
            # as mixing companies from different countries may lead to missing template elements.
            pt_companies = self.env.companies.filtered(lambda c: c.country_code == 'PT')
            report = self._get_report(report_ref)
            individual_company_reports = self._l10n_pt_templates_with_print_version()
            # 'account.report_invoice_with_payments' are rendered as separate documents, so there are no template issues
            individual_company_reports.remove('account.report_invoice_with_payments')
            if (
                report.report_name in individual_company_reports
                and pt_companies
                and pt_companies != self.env.companies
            ):
                raise UserError(_("It is not possible to print documents with the template %s for Portuguese and "
                                  "non-Portuguese companies at the same time.", report.name))
        # Every print (printing, sending, downloading) goes through here, an HTML preview does not:
        # only a print counts towards the "Original" and "2ª Via" of a PT document.
        return super(IrActionsReport, self.with_context(l10n_pt_print=True))._pre_render_qweb_pdf(
            report_ref, res_ids=res_ids, data=data,
        )

    def _l10n_pt_report_compliance(self, model, res_ids, compute_hash=False):
        """
        Ensure compliance with PT requirements by:
        - Triggering the computation of missing hashes for documents before printing.
        - Verifying the pre-requisites to generate the QR code.
        The print version (original or reprint) is kept by `l10n.pt.attachment`, per print.
        """
        records = self.env[model].browse(res_ids)
        if compute_hash:
            records._l10n_pt_compute_missing_hashes()
            for record in records:
                record.l10n_pt_verify_prerequisites_qr_code()

    def _l10n_pt_invoice_report_compliance(self, report_ref, res_ids, data=None):
        """
        Rendering an invoice report, any report flagged as one (a partner's template, a Studio copy),
        generates the invoices: it issues them (`account.move._l10n_pt_issue`). A pro-forma does not.
        """
        if (
            not self._is_invoice_report(report_ref)
            or (data or {}).get('proforma')
            or self.env.context.get('proforma_invoice')
        ):
            return
        invoices = self.env['account.move'].browse(res_ids)
        invoices._l10n_pt_issue()
        for invoice in invoices:
            invoice.l10n_pt_verify_prerequisites_qr_code()

    def _render_qweb_pdf_prepare_streams(self, report_ref, data, res_ids=None):
        if self._get_report(report_ref).report_name == 'account.report_hash_integrity':
            self._l10n_pt_report_compliance('account.move', res_ids, compute_hash=True)
        self._l10n_pt_invoice_report_compliance(report_ref, res_ids, data)
        return super()._render_qweb_pdf_prepare_streams(report_ref, data, res_ids)

    def _render_qweb_html(self, report_ref, docids, data=None):
        if self._get_report(report_ref).report_name == 'account.report_hash_integrity':
            self._l10n_pt_report_compliance('account.move', docids, compute_hash=True)
        self._l10n_pt_invoice_report_compliance(report_ref, docids, data)
        return super()._render_qweb_html(report_ref, docids, data=data)

    def _get_rendering_context(self, report, docids, data):
        data = super()._get_rendering_context(report, docids, data)
        data['l10n_pt_certification_number'] = PT_CERTIFICATION_NUMBER
        return data

    def _render_template(self, template, values=None):
        """
        EXTEND base. PT documents are rendered through `l10n.pt.attachment`, which keeps their first print.
        This allows satisfying two PT Certification requirements:
        - Documents should inform whether the printed version is an original or reprint
        - Document should remain the same even if there are changes to the partner after first print (for
        example, the partner's address changes after first print).
        """
        docs = values.get('docs')
        # When rendering templates for any PT documents that require indicating whether it is an original or reprint,
        # call `_get_l10n_pt_versioned_report_html()`
        if (
                not self.env.context.get('ignore_pt_versioning')
                and template in self._l10n_pt_templates_with_print_version()
                and docs and docs.filtered(lambda d: d.company_id.country_code == 'PT')
        ):
            htmls = []
            for doc in docs:
                # Render templates separately, so Portuguese documents will have their binaries saved, and
                # will indicate whether they are original or reprinted.
                values['docs'] = doc
                values['doc_ids'] = doc.ids
                if doc.company_id.country_code == 'PT':
                    html = self.env['l10n.pt.attachment']._get_l10n_pt_report_html(doc, template, values)
                else:
                    html = super()._render_template(template, values)
                htmls.append(html)
            return b''.join(htmls)
        return super()._render_template(template, values)

    def _l10n_pt_templates_with_print_version(self):
        """ Returns the templates for Portuguese documents that require the print version """
        return ['account.report_invoice', 'account.report_invoice_with_payments', 'account.report_payment_receipt']
