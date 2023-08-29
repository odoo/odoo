# -*- coding: utf-8 -*-
import io
from zlib import error as zlib_error
try:
    from PyPDF2.errors import PdfStreamError, PdfReadError
except ImportError:
    from PyPDF2.utils import PdfStreamError, PdfReadError

from odoo import _, models
from odoo.tools import format_amount, format_date, pdf


class IrActionsReport(models.Model):
    _inherit = 'ir.actions.report'

    def _render_qweb_pdf_prepare_streams(self, report_ref, data, res_ids=None):
        result = super()._render_qweb_pdf_prepare_streams(report_ref, data, res_ids=res_ids)
        if self._get_report(report_ref).report_name != 'sale.report_saleorder':
            return result

        orders = self.env['sale.order'].browse(res_ids)

        for order in orders:
            initial_stream = result[order.id]['stream']
            if initial_stream:
                order_template = order.sale_order_template_id
                record = order_template or order.company_id
                header = record.sale_header
                footer = record.sale_footer

                included_product_docs = self.env['product.document']
                for line in order.order_line:
                    documents = (
                        line.product_id.product_document_ids
                        or line.product_template_id.product_document_ids
                    )
                    doc_to_include = documents.filtered(lambda d: d.attached_on == 'inside')
                    included_product_docs = included_product_docs | doc_to_include

                if not header and not included_product_docs and not footer:
                    continue

                IrBinary = self.env['ir.binary']
                pdf_data = []
                if header:
                    header_stream = IrBinary._record_to_stream(record, 'sale_header').read()
                    pdf_data.append(header_stream)
                for included_doc in included_product_docs:
                    doc_stream = IrBinary._record_to_stream(included_doc, 'datas').read()
                    pdf_data.append(doc_stream)
                pdf_data.append((initial_stream).getvalue())
                if footer:
                    footer_stream = IrBinary._record_to_stream(record, 'sale_footer').read()
                    pdf_data.append(footer_stream)

                try:
                    form_fields = self._get_form_fields_mapping(order)
                    stream = io.BytesIO(pdf.merge_pdf(pdf_data, form_fields))
                    result[order.id].update({'stream': stream})
                except (ValueError, PdfStreamError, PdfReadError, TypeError, zlib_error,
                        NotImplementedError):
                    record._message_log(body=_(
                        "There was an error when trying to merge headers and footers to the "
                        "original PDF.\n Please make sure the source file are valid."
                    ))

        return result

    def _get_form_fields_mapping(self, order):
        """ Dictionary mapping specific pdf fields name to Odoo fields data.
        Override this method to add new fields to the mapping.

        :param recordset order: sale.order record
        :rtype: dict
        :return: mapping of fields name to Odoo fields data

        Note: order.ensure_one()
        """
        order.ensure_one()
        tz = order.partner_id.tz or self.env.user.tz or 'UTC'
        env = self.with_context(use_babel=True).env
        currency_id = order.currency_id
        form_fields_mapping = {
            'name': order.name,
            'partner_id__name': order.partner_id.name,
            'user_id__name': order.user_id.name,
            'amount_untaxed': format_amount(env, order.amount_untaxed, currency_id),
            'amount_total': format_amount(env, order.amount_total, currency_id),
            'commitment_date': format_date(env, order.commitment_date, tz=tz),
            'validity_date': format_date(env, order.validity_date, tz=tz),
            'client_order_ref': order.client_order_ref or '',
        }
        return form_fields_mapping
