# Part of Odoo. See LICENSE file for full copyright and licensing details.

import base64
import io
import json

from odoo import _, api, models
from odoo.tools import format_amount, format_date, format_datetime, pdf
from odoo.tools.pdf import (
    NameObject,
    NumberObject,
    PdfFileReader,
    PdfFileWriter,
    createStringObject,
)


class IrActionsReport(models.Model):
    _inherit = 'ir.actions.report'

    def _render_qweb_pdf_prepare_streams(self, report_ref, data, res_ids=None):
        """Override to add and fill headers, footers and product documents to the sale quotation."""
        result = super()._render_qweb_pdf_prepare_streams(report_ref, data, res_ids=res_ids)
        if self._get_report(report_ref).report_name != 'sale.report_saleorder':
            return result

        orders = self.env['sale.order'].browse(res_ids)

        for order in orders:
            if order.state == 'sale':
                continue
            initial_stream = result[order.id]['stream']
            if initial_stream:
                quotation_documents = order.quotation_document_ids
                headers = quotation_documents.filtered(lambda doc: doc.document_type == 'header')
                footers = quotation_documents - headers
                has_product_document = any(line.product_document_ids for line in order.order_line)

                if not headers and not has_product_document and not footers:
                    continue

                form_fields_values_mapping = {}
                writer = PdfFileWriter()

                self_with_order_context = self.with_context(
                    use_babel=True, lang=order._get_lang() or self.env.user.lang
                )

                if headers:
                    for header in headers:
                        prefix = f'quotation_document_id_{header.id}__'
                        self_with_order_context._update_mapping_and_add_pages_to_writer(
                            writer, header, form_fields_values_mapping, prefix, order
                        )
                if has_product_document:
                    for line in order.order_line:
                        for doc in line.product_document_ids:
                            # Use both the id of the line and the doc as variants could use the same
                            # document.
                            prefix = f'sol_id_{line.id}_product_document_id_{doc.id}__'
                            self_with_order_context._update_mapping_and_add_pages_to_writer(
                                writer, doc, form_fields_values_mapping, prefix, order, line
                            )
                self._add_pages_to_writer(writer, initial_stream.getvalue())
                if footers:
                    for footer in footers:
                        prefix = f'quotation_document_id_{footer.id}__'
                        self_with_order_context._update_mapping_and_add_pages_to_writer(
                            writer, footer, form_fields_values_mapping, prefix, order
                        )
                pdf.fill_form_fields_pdf(writer, form_fields=form_fields_values_mapping)
                with io.BytesIO() as _buffer:
                    writer.write(_buffer)
                    stream = io.BytesIO(_buffer.getvalue())
                result[order.id].update({'stream': stream})

        return result

    @api.model
    def _update_mapping_and_add_pages_to_writer(
        self, writer, document, form_fields_values_mapping, prefix, order, order_line=None
    ):
        """ Update the mapping with the field-value of the document, and add the doc to the writer.

        Note: document.ensure_one(), order.ensure_one(), order_line and order_line.ensure_one()

        :param PdfFileWriter writer: the writer to which pages needs to be added
        :param recordset document: the document that needs to be added to the writer and get its
                                   form fields mapped. Either a quotation.document or a
                                   product.document.
        :param dict form_fields_values_mapping: the existing prefixed form field names - values that
                                                will be updated to add those of the current document
        :param str prefix: the prefix needed to update existing form field name, to be able to add
                           the correct values in fields with the same name but on different
                           documents, either customizable fields or dynamic fields of different sale
                           order lines.
        :param recordset order: the sale order from where to take the values
        :param recordset order_line: the sale order line from where to take the values (optional)
        :return: None
        """
        document.ensure_one()
        order.ensure_one()
        order_line and order_line.ensure_one()

        for form_field in document.form_field_ids:
            if form_field.path:  # Dynamic field
                field_value = self._get_value_from_path(form_field, order, order_line)
            else:  # Customizable field
                field_value = self._get_custom_value_from_order(
                    document, form_field.name, order, order_line
                )
            form_fields_values_mapping[prefix + form_field.name] = field_value

        # Avoid useless update of the pdf when no form field and just add the pdf
        prefix = prefix if document.form_field_ids else None
        decoded_document = base64.b64decode(document.datas)
        self._add_pages_to_writer(writer, decoded_document, prefix)

    @api.model
    def _get_value_from_path(self, form_field, order, order_line=None):
        """ Get the string value by following the path indicated in the record form_field.

        :param recordset form_field: sale.pdf.form.field that has a valid path.
        :param recordset order: sale.order from where the values and timezone need to be taken
        :param recordset order_line: sale.order.line from where the values need to be taken
                                     (optional, only for product.document)
        :return: value that need to be shown in the final pdf. Multiple values are joined by ', '
        :rtype: str
        """
        tz = order.partner_id.tz or order.env.user.tz or 'UTC'
        base_record = order_line or order
        path = form_field.path

        # If path = 'order_id.order_line.product_id.name'
        path = path.split('.')  # ['order_id', 'order_line', 'product_id', 'name']
        # Sudo to be able to follow the path set by the admin
        records = base_record.sudo().mapped('.'.join(path[:-1]))  # product.product(id1, id2, ...)
        field_name = path[-1]  # 'name'

        def _get_formatted_value(self):
            # self must be named so to be considered in the translation logic
            field_ = records._fields[field_name]
            field_type_ = field_.type
            for record_ in records:
                value_ = record_[field_name]
                if field_type_ == 'boolean':
                    formatted_value_ = _("Yes") if value_ else _("No")
                elif field_type_ == 'monetary':
                    currency_id_ = record_[field_.get_currency_field(record_)]
                    formatted_value_ = format_amount(
                        self.env, value_, currency_id_ or order.currency_id
                    )
                elif not value_ and field_type_ not in {'integer', 'float'}:
                    formatted_value_ = ''
                elif field_type_ == 'date':
                    formatted_value_ = format_date(self.env, value_)
                elif field_type_ == 'datetime':
                    formatted_value_ = format_datetime(self.env, value_, tz=tz, dt_format=False)
                elif field_type_ == 'selection' and value_:
                    formatted_value_ = dict(field_._description_selection(self.env))[value_]
                elif field_type_ in {'one2many', 'many2one', 'many2many'}:
                    formatted_value_ = ', '.join([v.display_name for v in value_])
                else:
                    formatted_value_ = str(value_)

                yield formatted_value_

        return ', '.join(_get_formatted_value(self))

    @api.model
    def _get_custom_value_from_order(self, document, form_field_name, order, order_line):
        """ Get the custom value of a form field directly from the order.

        :param recordset document: the document that needs to be added to the writer and get its
                                   form fields mapped. Either a quotation.document or a
                                   product.document.
        :param str form_field_name: the name of the form field as present in the PDF.
        :param recordset order: the sale order from where to take the existing mapping.
        :param recordset order_line: the sale order line linked to the document (optional)
        :return: value that need to be shown in the final pdf.
        :rtype: str
        """
        existing_mapping = json.loads(order.customizable_pdf_form_fields or '{}')
        if order_line:
            base_values = existing_mapping.get('line', {}).get(str(order_line.id), {})
        elif document.document_type == 'header':
            base_values = existing_mapping.get('header', {})
        else:
            base_values = existing_mapping.get('footer', {})
        custom_form_fields = base_values.get(str(document.id), {}).get('custom_form_fields', {})
        return custom_form_fields.get(form_field_name, "")

    @api.model
    def _add_pages_to_writer(self, writer, document, prefix=None):
        """Add a PDF doc to the writer and fill the form text fields present in the pages if needed.

        :param PdfFileWriter writer: the writer to which pages needs to be added
        :param bytes document: the document to add in the final pdf
        :param str prefix: the prefix needed to update existing form field name, if any, to be able
                           to add the correct values in fields with the same name but on different
                           documents, either customizable fields or dynamic fields of different sale
                           order lines. (optional)
        :return: None
        """
        reader = PdfFileReader(io.BytesIO(document), strict=False)

        field_names = set()
        if prefix:
            field_names = reader.getFormTextFields()

        for page_id in range(reader.getNumPages()):
            page = reader.getPage(page_id)
            if prefix and page.get('/Annots'):
                # Modifying the annots that hold every information about the form fields
                for j in range(len(page['/Annots'])):
                    reader_annot = page['/Annots'][j].getObject()
                    if reader_annot.get('/T') in field_names:
                        # Prefix all form fields in the document with the document identifier.
                        # This is necessary to know which value needs to be taken when filling the forms.
                        form_key = reader_annot.get('/T')
                        new_key = prefix + form_key

                        # Modifying the form flags to force some characteristics
                        # 1. make all text fields read-only
                        # 2. make all text fields support multiline
                        form_flags = reader_annot.get('/Ff', 0)
                        readonly_flag = 1  # 1st bit sets readonly
                        multiline_flag = 1 << 12  # 13th bit sets multiline text
                        new_flags = form_flags | readonly_flag | multiline_flag

                        reader_annot.update({
                            NameObject("/T"): createStringObject(new_key),
                            NameObject("/Ff"): NumberObject(new_flags),
                        })
            writer.addPage(page)
