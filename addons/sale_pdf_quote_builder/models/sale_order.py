# Part of Odoo. See LICENSE file for full copyright and licensing details.

import json

from odoo import _, api, fields, models

DEFAULT_FORM_FIELDS_MAPPING = {'header': {}, 'line': {}, 'footer': {}}


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    is_pdf_quote_builder_active = fields.Boolean(string="Use PDF Quote Builder")
    quotation_document_ids = fields.Many2many(
        string="Headers/Footers",
        comodel_name='quotation.document',
        compute='_compute_quotation_document_ids',
        store=True,
        readonly=False,
    )
    customizable_pdf_form_fields = fields.Json(
        string="Customizable PDF Form Fields",
        compute='_compute_customizable_pdf_form_fields',
        store=True,
        readonly=False,
    )

    # === COMPUTE METHODS === #

    @api.depends('is_pdf_quote_builder_active', 'sale_order_template_id')
    def _compute_quotation_document_ids(self):
        for order in self:
            if not order.is_pdf_quote_builder_active:
                order.quotation_document_ids = self.env['quotation.document']
            elif order.sale_order_template_id:
                template = order.sale_order_template_id
                order.quotation_document_ids = template.sale_header_ids + template.sale_footer_ids
            else:
                quotation_documents = self.env['quotation.document'].search([], order='sequence')
                headers = quotation_documents.filtered(lambda doc: doc.document_type == 'header')
                footers = quotation_documents - headers
                order.quotation_document_ids = self.env['quotation.document']
                if headers:
                    order.quotation_document_ids += headers[0]
                if footers:
                    order.quotation_document_ids += footers[0]

    @api.depends('quotation_document_ids', 'order_line.product_document_ids', 'is_pdf_quote_builder_active')
    def _compute_customizable_pdf_form_fields(self):
        """ Compute the json of the customizable_pdf_form_fields field.

        The dependencies on the selected documents ensure that a newly added files could be fill
        immediately.

        The resulting json would look like this:
        {
            "header": {
                document_1.id: {
                    "document_name": document1.name,
                    "custom_form_fields": {
                        "form_field_1": "custom value",
                        "form_field_2": "Ducks are funny",
                        ...
                    }
                },
                document_2.id: {...},
                ...
            },
            "line": {
                sale_order_line_1.id: {document_3.id: {...}, ... }, ...
            },
            "footer": {
                document_4.id: {...}, ...
            },
        }
        """
        for order in self:
            if not order.is_pdf_quote_builder_active:
                continue
            if not isinstance(order.id, int):
                # Avoid computing with NewId when adding a line
                order.customizable_pdf_form_fields = json.dumps(DEFAULT_FORM_FIELDS_MAPPING)
                continue
            custom_content_mapping = {'header': {}, 'line': {}, 'footer': {}}
            existing_mapping = (
                order.customizable_pdf_form_fields
                and json.loads(order.customizable_pdf_form_fields)
                or DEFAULT_FORM_FIELDS_MAPPING
            )

            existing_mapping = existing_mapping or custom_content_mapping

            quotation_documents = order.quotation_document_ids
            headers = quotation_documents.filtered(lambda doc: doc.document_type == 'header')
            footers = quotation_documents - headers
            for header in headers:
                header._update_custom_content_map(
                    custom_content_mapping['header'], existing_mapping['header']
                )
            for line in order.order_line:
                for product_document in line.product_document_ids:
                    product_document._update_custom_content_map(
                        line, custom_content_mapping['line'], existing_mapping['line']
                    )
            for footer in footers:
                footer._update_custom_content_map(
                    custom_content_mapping['footer'], existing_mapping['footer']
                )

            order.customizable_pdf_form_fields = json.dumps(custom_content_mapping)

    # === ACTION METHODS === #

    def action_toggle_is_pdf_quote_builder_active(self):
        """ Toggle the field `is_pdf_quote_builder_active`. """
        self.ensure_one()
        self.is_pdf_quote_builder_active = not self.is_pdf_quote_builder_active

    def get_update_included_pdf_params(self):
        self.ensure_one()
        quotation_documents = self.env['quotation.document'].search([], order='sequence')
        headers_available = quotation_documents.filtered(lambda doc: doc.document_type == 'header')
        footers_available = quotation_documents.filtered(lambda doc: doc.document_type == 'footer')
        selected_documents = self.quotation_document_ids
        selected_headers = selected_documents.filtered(lambda doc: doc.document_type == 'header')
        selected_footers = selected_documents - selected_headers
        lines_params = []
        for line in self.order_line:
            if line.available_product_document_ids:
                lines_params.append({'name': line.name, 'id': line.id, 'files': [{
                    'name': doc.name.rstrip('.pdf'),
                    'id': doc.id,
                    'is_selected': doc in line.product_document_ids,
                } for doc in line.available_product_document_ids]})
        dialog_params = {
            'headers': {'name': _("Header"), 'files': [{
                'name': header.name, 'id': header.id, 'is_selected': header in selected_headers
            } for header in headers_available]},
            'lines': lines_params,
            'footers': {'name': _("Footer"), 'files': [{
                'name': footer.name, 'id': footer.id, 'is_selected': footer in selected_footers
            } for footer in footers_available]},
        }
        return dialog_params

    # === BUSINESS METHODS === #

    def save_included_pdf(self, selected_pdf):
        """ Configure the PDF that should be included in the PDF quote builder for a given quote

        Note: self.ensure_one()

        :param dic selected_pdf: Dictionary of all the sections linked to their header_footer or
                                 product_document ids, in the format: {
                                    'header': [doc_id],
                                    'lines': [{line_id: [doc_id]}],
                                    'footer': [doc_id]
                                }
        :return: None
        """
        self.ensure_one()
        quotation_doc = self.env['quotation.document']
        selected_headers = quotation_doc.browse(selected_pdf['header'])
        selected_footers = quotation_doc.browse(selected_pdf['footer'])
        self.quotation_document_ids = selected_headers.ids + selected_footers.ids
        for line in self.order_line:
            selected_lines = self.env['product.document'].browse(
                selected_pdf['lines'].get(str(line.id))
            )
            line.product_document_ids = selected_lines.ids

    def save_new_custom_content(self, document_type, form_field, content):
        """ Modify the content link to a form field in the custom content mapping of an order.

        Note: self.ensure_one()

        :param str document_type: The document type where the for field is. Either 'header_footer'
                                  or 'product_document'.
        :param str form_field: The form field in the custom content mapping.
        :param str content: The content of the form field in the custom content mapping.
        :return: None
        """
        self.ensure_one()
        mapping = json.loads(self.customizable_pdf_form_fields)
        mapping[document_type][form_field] = content
        self.customizable_pdf_form_fields = json.dumps(mapping)
