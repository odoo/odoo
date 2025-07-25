# Part of Odoo. See LICENSE file for full copyright and licensing details.

import json

from odoo import _, api, fields, models


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    def _default_quotation_document_ids(self):
        return self.env['quotation.document'].search([
            *self.env['quotation.document']._check_company_domain(self.env.company),
            ('quotation_template_ids', '=', False),
            ('add_by_default', '=', True),
        ])

    available_quotation_document_ids = fields.Many2many(
        string="Available Quotation Documents",
        comodel_name='quotation.document',
        compute='_compute_available_quotation_document_ids',
    )
    is_pdf_quote_builder_available = fields.Boolean(
        compute='_compute_is_pdf_quote_builder_available',
    )
    quotation_document_ids = fields.Many2many(
        string="Headers/Footers",
        comodel_name='quotation.document',
        default=_default_quotation_document_ids,
        readonly=False,
        check_company=True,
    )
    customizable_pdf_form_fields = fields.Json(
        string="Customizable PDF Form Fields",
        readonly=False,
    )

    # === COMPUTE METHODS === #

    @api.depends('sale_order_template_id')
    def _compute_available_quotation_document_ids(self):
        for order in self:
            order.available_quotation_document_ids = self.env['quotation.document'].search(
                self.env['quotation.document']._check_company_domain(order.company_id),
                order='sequence',
            ).filtered(lambda doc:
                # templates are available only to salesman
                not (templates := doc.sudo().quotation_template_ids)
                or order.sale_order_template_id in templates
            )

    @api.depends(
        'available_quotation_document_ids',
        'order_line',
        'order_line.available_product_document_ids',
    )
    def _compute_is_pdf_quote_builder_available(self):
        for order in self:
            order.is_pdf_quote_builder_available = bool(
                order.available_quotation_document_ids
                or order.order_line.available_product_document_ids
            )

    # === ONCHANGE METHODS === #

    @api.onchange('sale_order_template_id')
    def _onchange_sale_order_template_id(self):
        super()._onchange_sale_order_template_id()

        # Remove documents which are no longer available.
        self.quotation_document_ids &= self.available_quotation_document_ids

        if not self.sale_order_template_id.quotation_document_ids:
            return
        self.quotation_document_ids |= self.sale_order_template_id.quotation_document_ids.filtered(
            lambda doc: doc.company_id.id in [False, self.company_id.id] and doc.add_by_default
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

        available_docs = self.available_quotation_document_ids | self.quotation_document_ids
        headers_available = available_docs.filtered(
            lambda doc: doc.document_type == 'header'
        )
        footers_available = available_docs.filtered(
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
                        'is_selected': doc in line.sudo().product_document_ids, # User should be
                        # able to access all product documents even without sales access
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
