# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import models, _
from odoo.exceptions import UserError

import io


class IrActionsReport(models.Model):
    _inherit = 'ir.actions.report'

    def _get_rendering_context(self, report, docids, data):
        data = super()._get_rendering_context(report, docids, data)
        if report.report_name == 'stock.report_reception_report_label' and not docids:
            docids = data['docids']
            docs = self.env[report.model].browse(docids)
            data.update({
                'doc_ids': docids,
                'docs': docs,
            })
        return data

    def _render_qweb_pdf_prepare_streams(self, report_ref, data, res_ids=None):
        if self._get_report(report_ref).report_name != 'stock.report_lot_label':
            return super()._render_qweb_pdf_prepare_streams(report_ref, data, res_ids=res_ids)

        if not data:
            data = {}
        data.setdefault('report_type', 'pdf')

        # access the report details with sudo() but evaluation context as current user
        report_sudo = self._get_report(report_ref)

        if self.get_wkhtmltopdf_state() == 'install':
            # wkhtmltopdf is not installed
            # the call should be catched before (cf /report/check_wkhtmltopdf) but
            # if get_pdf is called manually (email template), the check could be
            # bypassed
            raise UserError(
                _("Unable to find Wkhtmltopdf on this system. The PDF can not be created."))

        # Disable the debug mode in the PDF rendering in order to not split the assets bundle
        # into separated files to load. This is done because of an issue in wkhtmltopdf
        # failing to load the CSS/Javascript resources in time.
        # Without this, the header/footer of the reports randomly disappear
        # because the resources files are not loaded in time.
        # https://github.com/wkhtmltopdf/wkhtmltopdf/issues/2083
        additional_context = {'debug': False}

        html = self.with_context(
            **additional_context)._render_qweb_html(report_ref, res_ids, data=data)[0]

        bodies, html_ids, header, footer, specific_paperformat_args = self.with_context(
            **additional_context)._prepare_html(html, report_model=report_sudo.model)

        if report_sudo.attachment and sorted(res_ids) != sorted(html_ids):
            raise UserError(_(
                "The report's template %r is wrong, please contact your administrator. \n\n"
                "Can not separate file to save as attachment because the report's template does not contains the"
                " attributes 'data-oe-model' and 'data-oe-id' on the div with 'article' classname.",
                self.name,
            ))

        pdf_content = self._run_wkhtmltopdf(
            bodies,
            report_ref=report_ref,
            header=header,
            footer=footer,
            landscape=self._context.get('landscape'),
            specific_paperformat_args=specific_paperformat_args,
            set_viewport_size=self._context.get('set_viewport_size'),
        )
        pdf_content_stream = io.BytesIO(pdf_content)

        return {
            False: {
                'stream': pdf_content_stream,
                'attachment': None
            }
        }
