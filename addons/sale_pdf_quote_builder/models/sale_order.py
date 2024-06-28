# Part of Odoo. See LICENSE file for full copyright and licensing details.

import json

from odoo import _, api, fields, models

from odoo.addons.sale_pdf_quote_builder.const import DEFAULT_FORM_FIELD_PATH_MAPPING


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    is_pdf_quote_builder_active = fields.Boolean(string="Use PDF Quote Builder")
    sale_header_ids = fields.Many2many(
        string="Headers",
        comodel_name='sale.pdf.header.footer',
        relation='sale_header_sale_order_rel',
        domain=[('document_type', '=', 'header')],
        compute='_compute_sale_header_and_sale_footer_ids',
        store=True,
        readonly=False,
    )
    sale_footer_ids = fields.Many2many(
        string="Footers",
        comodel_name='sale.pdf.header.footer',
        relation='sale_footer_sale_order_rel',
        domain=[('document_type', '=', 'footer')],
        compute='_compute_sale_header_and_sale_footer_ids',
        store=True,
        readonly=False,
    )
    # TODO edm: could be back to a single field then
    customizable_pdf_form_fields = fields.Json(
        string="Customizable PDF Form Fields",
        compute='_compute_custom_content_lines',
        store=True,
        readonly=False,
        required=True,
    )

    # === COMPUTE METHODS === #

    @api.depends('is_pdf_quote_builder_active', 'sale_order_template_id')
    def _compute_sale_header_and_sale_footer_ids(self):
        for order in self:
            if not order.is_pdf_quote_builder_active:
                order.sale_header_ids = order.sale_footer_ids = self.env['sale.pdf.header.footer']
            elif order.sale_order_template_id:
                order.sale_header_ids = order.sale_order_template_id.sale_header_ids
                order.sale_footer_ids = order.sale_order_template_id.sale_footer_ids
            else:
                sale_headers_footers = self.env['sale.pdf.header.footer'].search(
                    [('quotation_template_ids', "=", False)]
                )
                headers = sale_headers_footers.filtered(lambda doc: doc.document_type == 'header')
                if headers:
                    order.sale_header_ids = [headers[0].id]
                else:
                    order.sale_header_ids = self.env['sale.pdf.header.footer']
                footers = sale_headers_footers - headers
                if footers:
                    order.sale_footer_ids = [footers[0].id]
                else:
                    order.sale_header_ids = self.env['sale.pdf.header.footer']

    @api.depends('sale_header_ids', 'sale_footer_ids', 'order_line.product_document_ids')
    def _compute_custom_content_lines(self):
        # We depend on the different linked documents so that if a document is uploaded that adds
        # some new custom fields, those could be immediately fill too. Would still need to reload as
        # we don't want to depend on available documents.
        form_field_path_map = json.loads(self.env['ir.config_parameter'].sudo().get_param(
            'sale_pdf_quote_builder.form_field_path_mapping', DEFAULT_FORM_FIELD_PATH_MAPPING
        ))
        header_footer_items = form_field_path_map.get("header_footer").items()
        product_document_items = form_field_path_map.get("product_document").items()
        custom_content_map = {
            'header_footer': {field: "" for field, path in header_footer_items if not path},
            'product_document': {field: "" for field, path in product_document_items if not path},
        }
        for order in self:
            if order.customizable_pdf_form_fields:
                existing_mapping = json.loads(order.customizable_pdf_form_fields)
                for doc_type, mapping in existing_mapping.items():
                    for form_field, content in mapping.items():
                        is_valid_doc_type = doc_type in custom_content_map
                        is_valid_form_field = form_field in custom_content_map[doc_type]
                        # Add the existing content values only for valid (thus existing) form fields
                        if is_valid_doc_type and is_valid_form_field and content:
                            custom_content_map[doc_type][form_field] = content

            order.customizable_pdf_form_fields = json.dumps(custom_content_map)
            print(order.customizable_pdf_form_fields)

    # === ACTION METHODS === #

    def action_toggle_is_pdf_quote_builder_active(self):
        """ Toggle the field `is_pdf_quote_builder_active`. """
        self.ensure_one()
        self.is_pdf_quote_builder_active = not self.is_pdf_quote_builder_active

    def action_update_included_pdf(self):
        self.ensure_one()
        all_headers_footers = self.env['sale.pdf.header.footer'].search([])
        headers_available = all_headers_footers.filtered(lambda doc: doc.document_type == 'header')
        footers_available = all_headers_footers.filtered(lambda doc: doc.document_type == 'footer')
        lines_params = []
        for line in self.order_line:
            if line.available_product_document_ids:
                lines_params.append({'name': line.name, "id": line.id, 'files': [{
                    "name": doc.name.rstrip('.pdf'),
                    "id": doc.id,
                    "is_selected": doc in line.product_document_ids,
                } for doc in line.available_product_document_ids]})
        dialog_params = {
            "sale_order_id": self.id,
            "headers": {'name': _("Header"), 'files': [{
                "name": header.name, "id": header.id, "is_selected": header in self.sale_header_ids
            } for header in headers_available]},
            "lines": lines_params,
            "footers": {'name': _("Footer"), 'files': [{
                "name": footer.name, "id": footer.id, "is_selected": footer in self.sale_footer_ids
            } for footer in footers_available]},
        }
        return {
            'type': 'ir.actions.client',
            'tag': 'actionSaleUpdateIncludedPdf',
            "params": dialog_params,
        }

    # === BUSINESS METHODS === #

    def save_included_pdf(self, selected_pdf):
        """ Configure the PDF that should be included in the PDF quote builder for a given quote

        :param dic selected_pdf: Dictionary of all the sections linked to their header_footer or
                                 product_document ids, in the format: {
                                    'header': [doc_id],
                                    'lines': [{line_id: [doc_id]}],
                                    'footer': [doc_id]
                                }
        :return: None

        Note: self.ensure_one()
        """
        self.ensure_one()
        selected_headers = self.env['sale.pdf.header.footer'].browse(selected_pdf['header'])
        self.sale_header_ids = selected_headers.ids
        selected_footers = self.env['sale.pdf.header.footer'].browse(selected_pdf['footer'])
        self.sale_footer_ids = selected_footers.ids
        for line in self.order_line:
            selected_lines = self.env['product.document'].browse(
                selected_pdf['lines'].get(str(line.id))
            )
            line.product_document_ids = selected_lines.ids or self.env['product.document']

    def save_new_custom_content(self, document_type, form_field, content):
        """ Modify the content link to a form field in the custom content mapping of an order.

        :param str document_type: The document type where the for field is. Either 'header_footer'
                                  or 'product_document'.
        :param str form_field: The form field in the custom content mapping.
        :param str content: The content of the form field in the custom content mapping.
        :return: None

        Note: self.ensure_one()
        """
        self.ensure_one()
        mapping = json.loads(self.customizable_pdf_form_fields)
        mapping[document_type][form_field] = content
        self.customizable_pdf_form_fields = json.dumps(mapping)
