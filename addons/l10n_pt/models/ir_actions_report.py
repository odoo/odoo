import base64

from odoo import _, models
from odoo.exceptions import UserError

from odoo.addons.l10n_pt.const import PT_CERTIFICATION_NUMBER


class IrActionsReport(models.Model):
    _inherit = 'ir.actions.report'

    def _pre_render_qweb_pdf(self, report_ref, res_ids=None, data=None):
        # Check that only PT companies are selected, as mixing companies from different countries may lead to missing
        # template elements. The exception is 'account.account_invoices', where the controller by default selects all companies
        pt_companies = self.env.companies.filtered(lambda c: c.country_code == 'PT')
        report_name = self._get_report(report_ref).report_name
        if (
            report_name in self._l10n_pt_templates_with_print_version()
            and self.env.context.get('allow_multiple_companies')
            and pt_companies
            and pt_companies != self.env.companies
        ):
            raise UserError(_("It is not possible to print documents for Portuguese and non-Portuguese companies at the same time."))
        return super()._pre_render_qweb_pdf(report_ref, res_ids=res_ids, data=data)

    def _l10n_pt_report_compliance(self, model, res_ids, compute_hash=False, update_print_version=True):
        """
        Ensure compliance with PT requirements by:
        - Triggering the computation of missing hashes for documents before printing.
        - Updating the print version (original or reprint) to be displayed in documents.
        """
        Model = self.env[model]
        if compute_hash:
            Model._l10n_pt_compute_missing_hashes()
        if update_print_version:
            for record in Model.browse(res_ids):
                record.l10n_pt_verify_prerequisites_qr_code()
                record.update_l10n_pt_print_version()

    def _render_qweb_pdf_prepare_streams(self, report_ref, data, res_ids=None):
        report_ref_2_update_records_params = {
            'account.report_hash_integrity': ('account.move', True, False),
            'account.report_invoice_with_payments': ('account.move', True, True),
            'account.report_invoice': ('account.move', True, True),
            'account.report_payment_receipt': ('account.payment', False, True),
        }
        if params := report_ref_2_update_records_params.get(self._get_report(report_ref).report_name):
            model, compute_hash, update_print_version = params
            self._l10n_pt_report_compliance(model, res_ids, compute_hash, update_print_version)
        return super()._render_qweb_pdf_prepare_streams(report_ref, data, res_ids)

    def _get_rendering_context(self, report, docids, data):
        data = super()._get_rendering_context(report, docids, data)
        data['l10n_pt_certification_number'] = PT_CERTIFICATION_NUMBER
        return data

    def _get_l10n_pt_versioned_report_html(self, doc, template, values):
        """
        The first time a PT document is printed, it should indicate it is an "Original". Reprinted documents must
        mention "2ª Via". If there are any changes in the data of partners or of the company in between the original
        print and the reprint, the original data must be kept in the document. To do so, the binary of the original
        prints are saved in 'l10n.pt.attachment'. A reprint retrieves that binary, changes only the print version, and
        saves the binary of this reprint. Subsequent reprints retrieve the reprint binary.
        """
        L10nPtAttachment = self.env['l10n.pt.attachment']
        attachment = L10nPtAttachment.search([
            ('res_id', '=', doc.id),
            ('res_model', '=', values['doc_model']),
            ('report_name', '=', template),
            ('company_id', '=', doc.company_id.id),
        ])
        # Original print
        if doc.l10n_pt_print_version == 'original' and not attachment:
            html = super()._render_template(template, values)
            L10nPtAttachment.create({
                'res_id': doc.id,
                'res_model': values['doc_model'],
                'report_name': template,
                'original_binary': base64.b64encode(html),
            })
            return html
        # First reprint, ensures data is the same by retrieving the original binary and update reprint version
        if not attachment.reprint_binary:
            html = base64.b64decode(attachment.original_binary).decode('utf-8').replace(
                '<span id="l10n_pt_print_version">Original</span>',
                '<span id="l10n_pt_print_version">2ª Via</span>',
            ).encode('utf-8')
            attachment.reprint_binary = base64.b64encode(html)
            return html
        # Subsequent reprints
        return base64.b64decode(attachment.reprint_binary)

    def _render_template(self, template, values=None):
        docs = values.get('docs')
        # When rendering templates for any PT documents that require indicating whether it is an original or reprint,
        # call `_get_l10n_pt_versioned_report_html()`
        if (
            template in self._l10n_pt_templates_with_print_version()
            and docs and docs.filtered(lambda d: d.company_id.country_code == 'PT')
        ):
            if len(docs) == 1:
                return self._get_l10n_pt_versioned_report_html(docs[0], template, values)
            else:
                htmls = []
                for doc in docs:
                    # Render templates separately, so Portuguese documents will have their binaries saved, and
                    # will indicate whether they are original or reprinted.
                    values['docs'] = doc
                    values['doc_ids'] = doc.ids
                    if doc.company_id.country_code == 'PT':
                        html = self._get_l10n_pt_versioned_report_html(doc, template, values.copy())
                    else:
                        html = super()._render_template(template, values)
                    htmls.append(html)
                return b''.join(htmls).decode('utf-8')
        return super()._render_template(template, values)

    def _l10n_pt_templates_with_print_version(self):
        """ Returns the templates for Portuguese documents that require the print version """
        return ['account.report_invoice', 'account.report_invoice_with_payments', 'account.report_payment_receipt']
