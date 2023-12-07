# Part of Odoo. See LICENSE file for full copyright and licensing details.

import io

from PyPDF2 import PdfFileWriter, PdfFileReader
from PyPDF2.generic import NameObject, createStringObject

from odoo import models
from odoo.tools import format_amount, format_date, format_datetime, pdf


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
                header_record = order_template if order_template.sale_header else order.company_id
                footer_record = order_template if order_template.sale_footer else order.company_id
                has_header = bool(header_record.sale_header)
                has_footer = bool(footer_record.sale_footer)
                included_product_docs = self.env['product.document']
                doc_line_id_mapping = {}
                for line in order.order_line:
                    product_product_docs = line.product_id.product_document_ids
                    product_template_docs = line.product_template_id.product_document_ids
                    doc_to_include = (
                        product_product_docs.filtered(lambda d: d.attached_on == 'inside')
                        or product_template_docs.filtered(lambda d: d.attached_on == 'inside')
                    )
                    included_product_docs = included_product_docs | doc_to_include
                    doc_line_id_mapping.update({doc.id: line.id for doc in doc_to_include})

                if (not has_header and not included_product_docs and not has_footer):
                    continue

                IrBinary = self.env['ir.binary']
                writer = PdfFileWriter()
                if has_header:
                    header_stream = IrBinary._record_to_stream(header_record, 'sale_header').read()
                    self._add_pages_to_writer(writer, header_stream)
                if included_product_docs:
                    for doc in included_product_docs:
                        doc_stream = IrBinary._record_to_stream(doc, 'datas').read()
                        self._add_pages_to_writer(writer, doc_stream, doc_line_id_mapping[doc.id])
                        self._prefix_sol_form_fields(writer, doc_line_id_mapping[doc.id])
                self._add_pages_to_writer(writer, (initial_stream).getvalue())
                if has_footer:
                    footer_stream = IrBinary._record_to_stream(footer_record, 'sale_footer').read()
                    self._add_pages_to_writer(writer, footer_stream)

                form_fields = self._get_form_fields_mapping(order)
                pdf.fill_form_fields_pdf(writer, form_fields=form_fields)
                with io.BytesIO() as _buffer:
                    writer.write(_buffer)
                    stream = io.BytesIO(_buffer.getvalue())
                result[order.id].update({'stream': stream})

        return result

    def _add_pages_to_writer(self, writer, document, sol_id=None):
        prefix = f'{sol_id}_' if sol_id else ''
        reader = PdfFileReader(io.BytesIO(document), strict=False)
        sol_field_names = self._get_sol_form_fields_names()
        for page_id in range(0, reader.getNumPages()):
            page = reader.getPage(page_id)
            if sol_id and page.get('/Annots'):
                for j in range(0, len(page['/Annots'])):
                    writer_annot = page['/Annots'][j].getObject()
                    if writer_annot.get('/T') in sol_field_names:
                        writer_annot.update({
                            NameObject("/T"): createStringObject(prefix + writer_annot.get('/T'))
                        })
            writer.addPage(page)

    def _prefix_sol_form_fields(self, writer, sol_id):
        """ Prefix all form fields in the document with the sale order line id.
        This is necessary to avoid conflicts between fields with the same name.

        :param PdfFileWriter writer: PdfFileWriter instance
        :param int sol_id: sale.order.line id
        """
        prefix = f'{sol_id}_'
        sol_field_names = self._get_sol_form_fields_names()
        if hasattr(writer, 'pages'):
            nbr_pages = len(writer.pages)
        else:  # This method was renamed in PyPDF2 2.0
            nbr_pages = writer.getNumPages()
        for page_id in range(0, nbr_pages):
            page = writer.getPage(page_id)
            if not page.get('/Annots'):
                continue
            for j in range(0, len(page['/Annots'])):
                writer_annot = page['/Annots'][j].getObject()
                if writer_annot.get('/T') in sol_field_names:
                    writer_annot.update({
                        NameObject("/T"): createStringObject(prefix + writer_annot.get('/T'))
                    })

    def _get_sol_form_fields_names(self):
        """ List of specific pdf fields name for an order line that needs to be renamed in the pdf.
        Override this method to add new fields to the list.
        """
        return ['description', 'quantity', 'uom', 'price_unit', 'discount', 'product_sale_price',
                'taxes', 'tax_excl_price', 'tax_incl_price']

    def _get_form_fields_mapping(self, order):
        """ Dictionary mapping specific pdf fields name to Odoo fields data for a sale order.
        Override this method to add new fields to the mapping.

        :param recordset order: sale.order record
        :rtype: dict
        :return: mapping of fields name to Odoo fields data

        Note: order.ensure_one()
        """
        order.ensure_one()
        env = self.with_context(use_babel=True).env
        tz = order.partner_id.tz or self.env.user.tz or 'UTC'
        lang_code = order.partner_id.lang or self.env.user.lang
        form_fields_mapping = {
            'name': order.name,
            'partner_id__name': order.partner_id.name,
            'user_id__name': order.user_id.name,
            'amount_untaxed': format_amount(env, order.amount_untaxed, order.currency_id),
            'amount_total': format_amount(env, order.amount_total, order.currency_id),
            'delivery_date': format_datetime(env, order.commitment_date, tz=tz),
            'validity_date': format_date(env, order.validity_date, lang_code=lang_code),
            'client_order_ref': order.client_order_ref or '',
        }

        # Adding fields from each line, prefixed by the line_id to avoid conflicts
        for line in order.order_line:
            form_fields_mapping.update(self._get_sol_form_fields_mapping(line))

        return form_fields_mapping

    def _get_sol_form_fields_mapping(self, line):
        """ Dictionary mapping specific pdf fields name to Odoo fields data for a sale order line.

        Fields name are prefixed by the line id to avoid conflict between files.

        Override this method to add new fields to the mapping.

        :param recordset line: sale.order.line record
        :rtype: dict
        :return: mapping of prefixed fields name to Odoo fields data

        Note: line.ensure_one()
        """
        line.ensure_one()
        env = self.with_context(use_babel=True).env
        return {
            f'{line.id}_description': line.name,
            f'{line.id}_quantity': line.product_uom_qty,
            f'{line.id}_uom': line.product_uom.name,
            f'{line.id}_price_unit': format_amount(env, line.price_unit, line.currency_id),
            f'{line.id}_discount': line.discount,
            f'{line.id}_product_sale_price': format_amount(
                env, line.product_id.lst_price, line.product_id.currency_id
            ),
            f'{line.id}_taxes': ', '.join(tax.name for tax in line.tax_id),
            f'{line.id}_tax_excl_price': format_amount(env, line.price_subtotal, line.currency_id),
            f'{line.id}_tax_incl_price': format_amount(env, line.price_total, line.currency_id),
        }
