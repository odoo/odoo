# Part of Odoo. See LICENSE file for full copyright and licensing details.

import base64
import io
import json

from PyPDF2 import PdfFileReader, PdfFileWriter
from PyPDF2.generic import NameObject, createStringObject

from odoo import _, api, models
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

                form_fields_values_mapping = self.with_context(
                    use_babel=True,
                    lang=order._get_lang() or self.env.user.lang,
                )._get_form_fields_values_mapping(
                    order, all_form_fields, param_field_map
                )
                pdf.fill_form_fields_pdf(writer, form_fields=form_fields_values_mapping)
                with io.BytesIO() as _buffer:
                    writer.write(_buffer)
                    stream = io.BytesIO(_buffer.getvalue())
                result[order.id].update({'stream': stream})

        return result

    @api.model
    def _add_pages_to_writer(self, writer, document, all_form_fields=None, sol_id=None):
        """Add a PDF doc to the writer and fill the form fields present in the pages if needed.

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

        for page_id in range(reader.getNumPages()):
            page = reader.getPage(page_id)
            if all_form_fields and field_names and page.get('/Annots'):
                # Prefix all form fields in the product document with the sale order line id.
                # This is necessary to know the line from which the value needs to be taken when
                # filling the forms.
                for j in range(len(page['/Annots'])):
                    reader_annot = page['/Annots'][j].getObject()
                    if reader_annot.get('/T') in field_names:
                        form_key = reader_annot.get('/T')
                        new_key = prefix + form_key
                        reader_annot.update({NameObject("/T"): createStringObject(new_key)})
            writer.addPage(page)

    @api.model
    def _get_form_fields_values_mapping(self, order, all_form_fields, param_field_map):
        """Map specific pdf fields name to Odoo fields data values for a sale order.

        Note: order.ensure_one()

        :param recordset order: sale.order record from which to take the values
        :param set(str) all_form_fields: all the form field names present in the PDFs
        :param dict param_field_map: the map stored in the config parameter to assign the expected
                                     paths to the form fields. A form field not in that map will be
                                     ignored.
        :return: mapping of fields name to Odoo fields data
        :rtype: dict
        """
        order.ensure_one()
        tz = order.partner_id.tz or self.env.user.tz or 'UTC'
        return {
            field: self._get_formatted_field(field, order, tz, param_field_map)
            for field in all_form_fields
        }

    @api.model
    def _get_formatted_field(self, form_field_name, order, tz, param_field_map):
        """Format a field value from the extracted PDF string.

        Note: order.ensure_one()

        :param string form_field_name: field path
        :param recordset order: sale.order record from which to take the value, following the path
        :param dict translated_env: self.env, with the correct translation context to format amount,
                                    date and datetime
        :param str tz: the timezone used for rendering datetime
        :param dict param_field_map: the map stored in the config parameter to assign the expected
                                     paths to the form fields. A form field not in that map will be
                                     ignored.
        :return: formatted field value
        :rtype: string
        """
        def _get_formatted_value(self, field_name):
            # self must be named so to be considered in the translation logic
            field_ = records._fields[field_name]
            field_type_ = field_.type
            for record in records:
                value_ = record[field_name]
                if field_type_ == 'boolean':
                    formatted_value_ = _("Yes") if value_ else _("No")
                elif field_type_ == 'monetary':
                    currency_id_ = record[field_.get_currency_field(record)]
                    formatted_value_ = format_amount(
                        self.env, value_, currency_id_ or order.currency_id
                    )
                elif not value_:
                    formatted_value_ = ''
                elif field_type_ == 'date':
                    formatted_value_ = format_date(self.env, value_)
                elif field_type_ == 'datetime':
                    formatted_value_ = format_datetime(self.env, value_, tz=tz)
                elif field_type_ == 'selection' and value_:
                    formatted_value_ = dict(field_._description_selection(self.env))[value_]
                elif field_type_ in {'one2many', 'many2one', 'many2many'}:
                    formatted_value_ = ', '.join([v.display_name for v in value_])
                else:
                    formatted_value_ = str(value_)

                yield formatted_value_

        order.ensure_one()
        is_sol = form_field_name.startswith('sol_id_')

        if not is_sol:  # Header or footer
            record = order
            path = param_field_map.get('header_footer', {}).get(form_field_name)
        else:  # Product document
            prefix = form_field_name.split('__')[0]
            line_id = int(prefix[7:])
            record = order.order_line.browse(line_id)
            form_field_name = form_field_name.removeprefix(prefix + '__')
            path = param_field_map.get('product_document', {}).get(form_field_name)

        if not path:
            return ''

        # If path = 'order_id.order_line.product_id.name'
        path = path.split('.')  # ['order_id', 'order_line', 'product_id', 'name']
        # sudo to be able to follow the path set by the admin
        records = record.sudo().mapped('.'.join(path[:-1]))  # product.product(id1, id2, ...)
        field_name = path[-1]  # 'name'

        return ', '.join(_get_formatted_value(self, field_name))
