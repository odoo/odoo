# Part of Odoo. See LICENSE file for full copyright and licensing details.

import json

from odoo import _, api, fields, models


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    available_product_document_ids = fields.Many2many(
        string="Available Product Documents",
        comodel_name='quotation.document',
        compute='_compute_available_product_document_ids',
    )
    is_pdf_quote_builder_available = fields.Boolean(
        compute='_compute_is_pdf_quote_builder_available',
    )
    quotation_document_ids = fields.Many2many(
        string="Headers/Footers",
        comodel_name='quotation.document',
        readonly=False,
        check_company=True,
    )
    customizable_pdf_form_fields = fields.Json(
        string="Customizable PDF Form Fields",
        readonly=False,
    )

    # === COMPUTE METHODS === #

    @api.depends('sale_order_template_id')
    def _compute_available_product_document_ids(self):
        for order in self:
            order.available_product_document_ids = self.env['quotation.document'].search(
                self.env['quotation.document']._check_company_domain(self.company_id),
                order='sequence',
            ).filtered(lambda doc:
                self.sale_order_template_id in doc.quotation_template_ids
                or not doc.quotation_template_ids
            )

    @api.depends('available_product_document_ids', 'order_line', 'order_line.available_product_document_ids')
    def _compute_is_pdf_quote_builder_available(self):
        for order in self:
            order.is_pdf_quote_builder_available = bool(
                order.available_product_document_ids
                or order.order_line.available_product_document_ids
            )

    # === ACTION METHODS === #

    def get_update_included_pdf_params(self):
        if not self:
            return {
                'headers': {},
                'files': {},
                'footers': {},
            }
        self.ensure_one()
        existing_mapping = (
            self.customizable_pdf_form_fields
            and json.loads(self.customizable_pdf_form_fields)
        ) or {}

        headers_available = self.available_product_document_ids.filtered(
            lambda doc: doc.document_type == 'header'
        )
        footers_available = self.available_product_document_ids.filtered(
            lambda doc: doc.document_type == 'footer'
        )
        selected_documents = self.quotation_document_ids
        selected_headers = selected_documents.filtered(lambda doc: doc.document_type == 'header')
        selected_footers = selected_documents - selected_headers
        lines_params = []
        for line in self.order_line:
            if line.available_product_document_ids:
                lines_params.append({
                    'name': _("Product") + " > " + line.name.splitlines()[0],
                    'id': line.id,
                    'files': [{
                        'name': doc.name.rstrip('.pdf'),
                        'id': doc.id,
                        'is_selected': doc in line.product_document_ids,
                        'custom_form_fields': [{
                            'name': custom_form_field.name,
                            'value': existing_mapping.get('line', {}).get(str(line.id), {}).get(
                                str(doc.id), {}
                            ).get('custom_form_fields', {}).get(custom_form_field.name, ""),
                        } for custom_form_field in doc.form_field_ids.filtered(
                            lambda ff: not ff.path
                        )],
                    } for doc in line.available_product_document_ids]
                })
        dialog_params = {
            'headers': {'name': _("Header"), 'files': [{
                'id': header.id,
                'name': header.name,
                'is_selected': header in selected_headers,
                'custom_form_fields': [{
                    'name': custom_form_field.name,
                    'value': existing_mapping.get('header', {}).get(str(header.id), {}).get(
                        'custom_form_fields', {}
                    ).get(custom_form_field.name, ""),
                } for custom_form_field in header.form_field_ids.filtered(lambda ff: not ff.path)],
            } for header in headers_available]},
            'lines': lines_params,
            'footers': {'name': _("Footer"), 'files': [{
                'id': footer.id,
                'name': footer.name,
                'is_selected': footer in selected_footers,
                'custom_form_fields': [{
                    'name': custom_form_field.name,
                    'value': existing_mapping.get('footer', {}).get(str(footer.id), {}).get(
                        'custom_form_fields', {}
                    ).get(custom_form_field.name, ""),
                } for custom_form_field in footer.form_field_ids.filtered(lambda ff: not ff.path)],
            } for footer in footers_available]},
        }
        return dialog_params

    # === BUSINESS METHODS === #

    # FIXME EDM dead code below ?
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
