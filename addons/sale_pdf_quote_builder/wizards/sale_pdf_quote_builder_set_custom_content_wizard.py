# Part of Odoo. See LICENSE file for full copyright and licensing details.

import json

from odoo import Command, api, fields, models

from odoo.addons.sale_pdf_quote_builder.const import DEFAULT_FORM_FIELD_PATH_MAPPING


class SalePDFQuoteBuilderSetCustomContentWizard(models.TransientModel):
    _name = 'sale.pdf.quote.builder.set.custom.content.wizard'
    _description = "Sale PDF Quote Builder Customizable Fields Configurator Wizard"

    sale_order_id = fields.Many2one('sale.order', string="Sale Order")
    custom_content_wizard_line_ids = fields.One2many(
        'sale.pdf.quote.builder.set.custom.content.wizard.line', 'custom_content_wizard_id'
    )

    @api.onchange('sale_order_id')
    def _get_wizard_lines(self):
        """ Create wizard lines containing existing form fields not mapped to any path.
        """
        for wizard in self:
            wizard.custom_content_wizard_line_ids = [Command.clear()]
            form_field_path_map = json.loads(self.env['ir.config_parameter'].sudo().get_param(
                'sale_pdf_quote_builder.form_field_path_mapping', DEFAULT_FORM_FIELD_PATH_MAPPING
            ))
            mapping = {
                'header_footer': {
                    f: '' for f, p in form_field_path_map.get("header_footer").items() if not p
                },
                'product_document': {
                    f: '' for f, p in form_field_path_map.get("product_document").items() if not p
                },
            }
            if wizard.sale_order_id.customizable_pdf_form_fields:
                existing_mapping = json.loads(wizard.sale_order_id.customizable_pdf_form_fields)
                for doc_type, doc_mapping in existing_mapping.items():
                    if doc_type not in mapping:
                        # Don't add a content value for a form field that isn't valid anymore
                        continue
                    for form_field, content in doc_mapping.items():
                        if form_field not in mapping[doc_type]:
                            # Don't add a content value for a form field that isn't valid anymore
                            continue
                        if content:
                            mapping[doc_type][form_field] = content

            lines_vals = [
                {'document_type': doc_type, 'form_field': form_field, 'content': content}
                for doc_type, doc_mapping in mapping.items()
                for form_field, content in doc_mapping.items()
            ]

            wizard.custom_content_wizard_line_ids = [Command.create(v) for v in lines_vals]

    def validate_custom_content_configuration(self):
        """ Save this content mapping configuration on the sale order. """
        for wizard in self:
            wizard_lines = wizard.custom_content_wizard_line_ids
            so_wiz_lines = wizard_lines.filtered(lambda line: line.document_type == 'header_footer')
            sol_wiz_lines = wizard_lines - so_wiz_lines
            header_footer_contents = {l.form_field: l.content for l in so_wiz_lines if l.content}
            product_doc_contents = {l.form_field: l.content for l in sol_wiz_lines if l.content}
            new_mapping = {}
            if header_footer_contents:
                new_mapping['header_footer'] = header_footer_contents
            if product_doc_contents:
                new_mapping['product_document'] = product_doc_contents
            wizard.sale_order_id.customizable_pdf_form_fields = json.dumps(new_mapping)


class SalePDFQuoteBuilderSetCustomContentWizardLine(models.TransientModel):
    _name = 'sale.pdf.quote.builder.set.custom.content.wizard.line'
    _description = "SalePdfQuoteBuilderSetCustomContentWizardLine transient representation"

    custom_content_wizard_id = fields.Many2one(
        'sale.pdf.quote.builder.set.custom.content.wizard', required=True, ondelete='cascade'
    )
    document_type = fields.Selection(
        string="Document Type",
        selection=[('header_footer', "Header/Footer"), ('product_document', "Product Document")],
        required=True,
        readonly=True,
    )
    form_field = fields.Char(
        string="Form Field",
        help="Form Field Name as seen in the PF form",
        required=True,
        readonly=True,
    )
    content = fields.Char(default="", help="Content to fill the pdf for this sale order.")
