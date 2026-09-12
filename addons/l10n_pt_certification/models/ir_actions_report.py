import base64

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
                                  "non-Portuguese companies at the same time.") % report.name)
        return super()._pre_render_qweb_pdf(report_ref, res_ids=res_ids, data=data)

    def _l10n_pt_report_compliance(self, model, res_ids, compute_hash=False, update_print_version=True):
        """
        Ensure compliance with PT requirements by:
        - Triggering the computation of missing hashes for documents before printing.
        - Verifying the pre-requisites to generate the QR code.
        - Updating the print version (original or reprint) to be displayed in documents.
        """
        records = self.env[model].browse(res_ids)
        if compute_hash:
            self.env[model]._l10n_pt_compute_missing_hashes()
            for record in records:
                record.l10n_pt_verify_prerequisites_qr_code()
        if update_print_version:
            records.update_l10n_pt_print_version()

    def _render_qweb_pdf_prepare_streams(self, report_ref, data, res_ids=None):
        report_ref_2_report_compliance_params = {
            'account.report_hash_integrity': ('account.move', True, False),
            'account.report_invoice_with_payments': ('account.move', True, True),
            'account.report_invoice': ('account.move', True, True),
            'account.report_payment_receipt': ('account.payment', False, True),
        }
        if params := report_ref_2_report_compliance_params.get(self._get_report(report_ref).report_name):
            model, compute_hash, update_print_version = params
            self._l10n_pt_report_compliance(model, res_ids, compute_hash, update_print_version)
        return super()._render_qweb_pdf_prepare_streams(report_ref, data, res_ids)

    def _get_rendering_context(self, report, docids, data):
        data = super()._get_rendering_context(report, docids, data)
        data['l10n_pt_certification_number'] = PT_CERTIFICATION_NUMBER
        return data

    def _render_template(self, template, values=None):
        """
        EXTEND base. PT templates are saved as binaries in l10n.pt.attachment, and if a binary exist, the html is
        retrieved from there. This allows satisfying two PT Certification requirements:
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
                    html = base64.b64decode(
                        self.env['l10n.pt.attachment']._get_l10n_pt_report_binary(doc, template, values)
                    )
                else:
                    html = super()._render_template(template, values)
                htmls.append(html)
            return b''.join(htmls).decode('utf-8')
        return super()._render_template(template, values)

    def _l10n_pt_templates_with_print_version(self):
        """ Returns the templates for Portuguese documents that require the print version """
        return ['account.report_invoice', 'account.report_invoice_with_payments', 'account.report_payment_receipt']
