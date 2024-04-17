# Part of Odoo. See LICENSE file for full copyright and licensing details.

import base64
import io
import json

from PyPDF2 import PdfFileWriter, PdfFileReader
from PyPDF2.generic import NameObject, createStringObject

from odoo import models
from odoo.tools import format_amount, format_date, format_datetime, pdf

from odoo.addons.sale_pdf_quote_builder.const import DEFAULT_FORM_FIELD_PATH_MAPPING


class IrActionsReport(models.Model):
    _inherit = 'ir.actions.report'

    def _render_qweb_pdf_prepare_streams(self, report_ref, data, res_ids=None):
        """ Override to add and fill header, footer and product documents to the sale quotation."""
        result = super()._render_qweb_pdf_prepare_streams(report_ref, data, res_ids=res_ids)
        if self._get_report(report_ref).report_name != 'sale.report_saleorder':
            return result

        orders = self.env['sale.order'].browse(res_ids)

        IrConfigParameter = self.env['ir.config_parameter'].sudo()
        param_field_map = json.loads(IrConfigParameter.get_param(
            'sale_pdf_quote_builder.form_field_path_mapping', DEFAULT_FORM_FIELD_PATH_MAPPING
        ))

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
                        product_product_docs.filtered(lambda d: d.attached_on_sale == 'inside')
                        or product_template_docs.filtered(lambda d: d.attached_on_sale == 'inside')
                    )
                    included_product_docs = included_product_docs | doc_to_include
                    doc_line_id_mapping.update({doc.id: line.id for doc in doc_to_include})

                if (not has_header and not included_product_docs and not has_footer):
                    continue

                all_form_fields = set()
                writer = PdfFileWriter()

                if has_header:
                    decoded_header = base64.b64decode(header_record.sale_header)
                    self._add_pages_to_writer(writer, decoded_header, all_form_fields)
                if included_product_docs:
                    for doc in included_product_docs:
                        decoded_doc = base64.b64decode(doc.datas)
                        sol_id = doc_line_id_mapping[doc.id]
                        self._add_pages_to_writer(
                            writer, decoded_doc, all_form_fields, sol_id=sol_id
                        )
                self._add_pages_to_writer(writer, initial_stream.getvalue())
                if has_footer:
                    decoded_footer = base64.b64decode(footer_record.sale_footer)
                    self._add_pages_to_writer(writer, decoded_footer, all_form_fields)

                form_fields_values_mapping = self._get_form_fields_values_mapping(
                    order, all_form_fields, param_field_map
                )
                pdf.fill_form_fields_pdf(writer, form_fields=form_fields_values_mapping)
                with io.BytesIO() as _buffer:
                    writer.write(_buffer)
                    stream = io.BytesIO(_buffer.getvalue())
                result[order.id].update({'stream': stream})

        return result

    def _add_pages_to_writer(self, writer, document, all_form_fields=None, sol_id=None):
        """Add a PDF doc to the writer. Update the set of form fields present in the pages if needed

        :param PdfFileWriter writer: the writer to which pages needs to be added
        :param bytes document: the document to add in the final pdf
        :param set all_form_fields: the set of form fields present in the already added pages. It'll
                                    be updated with the new form fields if any when passed. Optional
        :param int sol_id: the sale order line id, to ensure the product document are filled with
                           the correct line information. Only for product documents.
        :return: None
        """
        prefix = f'sol_id_{sol_id}__' if sol_id else ''
        reader = PdfFileReader(io.BytesIO(document), strict=False)

        field_names = set()
        if all_form_fields is not None:
            field_names = reader.getFields()
            if field_names:
                all_form_fields.update([prefix + field_name for field_name in field_names])

        for page_id in range(0, reader.getNumPages()):
            page = reader.getPage(page_id)
            if all_form_fields and field_names and page.get('/Annots'):
                # Prefix all form fields in the product document with the sale order line id.
                # This is necessary to know the line from which the value needs to be taken when
                # filling the forms.
                for j in range(0, len(page['/Annots'])):
                    reader_annot = page['/Annots'][j].getObject()
                    if reader_annot.get('/T') in field_names:
                        form_key = reader_annot.get('/T')
                        new_key = prefix + form_key
                        reader_annot.update({NameObject("/T"): createStringObject(new_key)})
            writer.addPage(page)

    def _get_form_fields_values_mapping(self, order, all_form_fields, param_field_map):
        """ Dictionary mapping specific pdf fields name to Odoo fields data values for a sale order.

        :param recordset order: sale.order record from which to take the values
        :param set(str) all_form_fields: all the form field names present in the PDFs
        :param dict param_field_map: the map stored in the config parameter to assign the expected
                                     paths to the form fields. A form field not in that map will be
                                     ignored.
        :rtype: dict
        :return: mapping of fields name to Odoo fields data

        Note: order.ensure_one()
        """
        order.ensure_one()
        env = self.with_context(use_babel=True).env
        tz = order.partner_id.tz or self.env.user.tz or 'UTC'
        form_fields_mapping = {
            field: self._get_formatted_field(field, order, env, tz, param_field_map)
            for field in all_form_fields
        }

        return form_fields_mapping

    def _get_formatted_field(self, form_field_name, order, translated_env, tz, param_field_map):
        """ Format a field value from the extracted PDF string.

        :param string form_field_name: field path
        :param recordset order: sale.order record from which to take the value, following the path
        :param dict translated_env: self.env, with the correct translation context to format amount,
                                    date and datetime
        :param str tz: the timezone used for rendering datetime
        :param dict param_field_map: the map stored in the config parameter to assign the expected
                                     paths to the form fields. A form field not in that map will be
                                     ignored.
        :rtype: string
        :return: formatted field value

        Note: order.ensure_one()
        """
        def _get_formatted_value(value_):
            if field_type == 'boolean':
                formatted_value = _("Yes") if value_ else _("No")
            elif field_type == 'monetary':
                currency_id = records[field.get_currency_field(records)]
                formatted_value = format_amount(
                    translated_env, value_, currency_id or order.currency_id
                )
            elif field_type == 'date':
                formatted_value = format_date(translated_env, value_, lang_code=lang)
            elif field_type == 'datetime':
                formatted_value = format_datetime(translated_env, value_, tz=tz)
            elif field_type == 'selection' and value_:
                formatted_value = dict(field._description_selection(translated_env))[value_]
            elif field_type in {'one2many', 'many2one', 'many2many'}:
                formatted_value = ', '.join([v.display_name for v in value_])
            else:
                formatted_value = value_

            return '' if formatted_value is False else str(formatted_value)

        order.ensure_one()
        is_sol = form_field_name.startswith('sol_id_')

        if not is_sol:  # Header or footer
            record = order
            path = param_field_map.get('header_footer', {}).get(form_field_name)
        else:  # Product document
            prefix, *_ = form_field_name.split('__')
            line_id = int(prefix.lstrip('sol_id_'))
            record = order.order_line.browse(line_id)
            form_field_name = form_field_name.removeprefix(prefix + '__')
            path = param_field_map.get('product_document', {}).get(form_field_name)

        if not path:
            return ''

        path = path.split('.')
        records = record.mapped('.'.join(path[:-1]))
        field_name = path[-1]
        field = records._fields[field_name]
        field_type = field.type

        lang = order._get_lang() or self.env.user.lang
        context = {'lang': lang}
        formatted_values = ', '.join([_get_formatted_value(value[field_name]) for value in records])
        del context

        return formatted_values
