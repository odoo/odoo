# -*- coding: utf-8 -*-
import io

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
                for line in order.order_line:
                    product_product_docs = line.product_id.product_document_ids
                    product_template_docs = line.product_template_id.product_document_ids
                    doc_to_include = (
                        product_product_docs.filtered(lambda d: d.attached_on == 'inside')
                        or product_template_docs.filtered(lambda d: d.attached_on == 'inside')
                    )
                    included_product_docs = included_product_docs | doc_to_include

                if (not has_header and not included_product_docs and not has_footer):
                    continue

                IrBinary = self.env['ir.binary']
                so_form_fields = self._get_so_form_fields_mapping(order)
                pdf_data = []
                if has_header:
                    header_stream = IrBinary._record_to_stream(header_record, 'sale_header').read()
                    header_stream = pdf.fill_form_fields_pdf(header_stream, so_form_fields)
                    pdf_data.append(header_stream)
                if included_product_docs:
                    docs_streams = self._fill_sol_documents_fields(
                        order, included_product_docs, so_form_fields
                    )
                    pdf_data.extend(docs_streams)

                pdf_data.append((initial_stream).getvalue())
                if has_footer:
                    footer_stream = IrBinary._record_to_stream(footer_record, 'sale_footer').read()
                    footer_stream = pdf.fill_form_fields_pdf(footer_stream, so_form_fields)
                    pdf_data.append(footer_stream)

                stream = io.BytesIO(pdf.merge_pdf(pdf_data))
                result[order.id].update({'stream': stream})

        return result

    def _fill_sol_documents_fields(self, order, documents, so_form_fields):
        """ Fill sale order line documents fields with sale order and sale order lines fields data.

        :param recordset order: sale.order record
        :param recordset documents: product.document records
        :param dict so_form_fields: sale order fields data
        :return: a list of PDF
        :rtype: list of datastrings
        """
        IrBinary = self.env['ir.binary']
        docs_streams = []
        for line in order.order_line:
            if not documents:
                return docs_streams
            # Merge so and sol data, in case of the same field name: priority to the sol data
            sol_form_fields = so_form_fields | self._get_sol_form_fields_mapping(line)
            product_id = line.product_id.id
            template_id = line.product_template_id.id
            line_documents = documents.filtered(
                lambda d: (d.res_model == 'product.product' and d.res_id == product_id)
                          or (d.res_model == 'product.template' and d.res_id == template_id)
            )
            for doc in line_documents:
                doc_stream = IrBinary._record_to_stream(doc, 'datas').read()
                doc_stream = pdf.fill_form_fields_pdf(doc_stream, sol_form_fields)
                docs_streams.append(doc_stream)
            documents -= line_documents
        return docs_streams

    def _get_sol_form_fields_mapping(self, line):
        """ Dictionary mapping specific pdf fields name to Odoo fields data for a sale order line.
        Override this method to add new fields to the mapping.

        :param recordset line: sale.order.line record
        :rtype: dict
        :return: mapping of fields name to Odoo fields data

        Note: line.ensure_one()
        """
        line.ensure_one()
        env = self.with_context(use_babel=True).env
        form_fields_mapping = {
            'description': line.name,
            'quantity': line.product_uom_qty,
            'uom': line.product_uom.name,
            'price_unit': format_amount(env, line.price_unit, line.currency_id),
            'discount': line.discount,
            'product_sale_price': format_amount(
                env, line.product_id.lst_price, line.product_id.currency_id
            ),
            'taxes': ', '.join(tax.name for tax in line.tax_id),
            'tax_excl_price': format_amount(env, line.price_subtotal, line.currency_id),
            'tax_incl_price': format_amount(env, line.price_total, line.currency_id),
        }
        return form_fields_mapping

    def _get_so_form_fields_mapping(self, order):
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
        return form_fields_mapping
