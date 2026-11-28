from odoo import models
from odoo.exceptions import UserError

from odoo.addons.l10n_pt_certification.const import PT_CERTIFICATION_NUMBER


class IrActionsReport(models.Model):
    _inherit = 'ir.actions.report'

    def _pre_render_qweb_pdf(self, report_ref, res_ids=None, data=None):
        # As core: a report can be rendered for a single id, or for no record at all (data only).
        if isinstance(res_ids, int):
            res_ids = [res_ids]
        if res_ids and len(res_ids) > 1:
            # Check that, if multiple documents are printed at once, they are either all of PT companies
            # or all of other companies, as mixing companies from different countries may lead to
            # missing template elements.
            report = self._get_report(report_ref)
            individual_company_reports = self._l10n_pt_templates_with_print_version()
            # 'account.report_invoice_with_payments' are rendered as separate documents, so there are no template issues
            individual_company_reports.remove('account.report_invoice_with_payments')
            if report.report_name in individual_company_reports:
                companies = self.env[report.model].browse(res_ids).company_id
                pt_companies = companies.filtered(lambda c: c.country_code == 'PT')
                if pt_companies and pt_companies != companies:
                    raise UserError(self.env._("It is not possible to print documents with the template %s for Portuguese and "
                                               "non-Portuguese companies at the same time.", report.name))
        # Every print (printing, sending, downloading) goes through here, an HTML preview does not:
        # only a print counts towards the "Original" and "2ª Via" of a PT document.
        return super(IrActionsReport, self.with_context(l10n_pt_print=True))._pre_render_qweb_pdf(
            report_ref, res_ids=res_ids, data=data,
        )

    def _l10n_pt_report_compliance(self, records):
        """
        Make ``records`` printable as PT documents: sign those not signed yet, with the rest of their
        series, then check what their QR code needs. The print version (original or reprint) is kept
        by `l10n.pt.attachment`, per print.
        """
        records._l10n_pt_compute_missing_hashes()
        for record in records:
            record._l10n_pt_verify_prerequisites_qr_code()

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
            invoice._l10n_pt_verify_prerequisites_qr_code()

    def _l10n_pt_hash_integrity_report_compliance(self, report_ref):
        """
        Sign the invoices still missing a hash before core's integrity report checks them. That
        report is rendered for companies (``res.company`` docids), not for the invoices it covers.
        """
        if self._get_report(report_ref).report_name == 'account.report_hash_integrity':
            self.env['account.move']._l10n_pt_compute_missing_hashes()

    def _render_qweb_pdf_prepare_streams(self, report_ref, data, res_ids=None):
        self._l10n_pt_hash_integrity_report_compliance(report_ref)
        self._l10n_pt_invoice_report_compliance(report_ref, res_ids, data)
        return super()._render_qweb_pdf_prepare_streams(report_ref, data, res_ids)

    def _render_qweb_html(self, report_ref, docids, data=None):
        self._l10n_pt_hash_integrity_report_compliance(report_ref)
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
        docs = (values or {}).get('docs')
        if (
                not self.env.context.get('ignore_pt_versioning')
                and template in self._l10n_pt_templates_with_print_version()
                and docs and docs.filtered(lambda d: d._l10n_pt_country_ok())
        ):
            htmls = []
            for doc in docs:
                # One by one, so each PT document gets its own stored print and print version. The
                # documents a PT company receives (vendor bills, outbound payments) print as they are.
                values['docs'] = doc
                values['doc_ids'] = doc.ids
                if doc._l10n_pt_country_ok():
                    html = self.env['l10n.pt.attachment']._get_l10n_pt_report_html(doc, template, values)
                else:
                    html = super()._render_template(template, values)
                htmls.append(html)
            return b''.join(htmls)
        return super()._render_template(template, values)

    def _l10n_pt_templates_with_print_version(self):
        """ Returns the templates for Portuguese documents that require the print version """
        return ['account.report_invoice', 'account.report_invoice_with_payments', 'account.report_payment_receipt']
