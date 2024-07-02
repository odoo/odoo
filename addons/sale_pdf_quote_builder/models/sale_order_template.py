# Part of Odoo. See LICENSE file for full copyright and licensing details.

import json

from odoo import _, fields, models

from odoo.addons.sale_pdf_quote_builder import utils


class SaleOrderTemplate(models.Model):
    _inherit = 'sale.order.template'

    quotation_document_ids = fields.Many2many(
        string="Headers and footers",
        comodel_name='quotation.document',
        relation='header_footer_quotation_template_rel',
    )
    sale_header_ids = fields.Many2many(
        string="Headers",
        comodel_name='quotation.document',
        domain=[('document_type', '=', 'header')],
        compute='_compute_sale_header_and_sale_footer_ids',
        inverse='_inverse_sale_header_and_sale_footer_ids',
        readonly=False,  # TODO edm: order of args
        # Also TODO edm: recheck '' or "", you know you forgot some
    )
    sale_footer_ids = fields.Many2many(
        string="Footers",
        comodel_name='quotation.document',
        domain=[('document_type', '=', 'footer')],
        compute='_compute_sale_header_and_sale_footer_ids',
        inverse='_inverse_sale_header_and_sale_footer_ids',
        readonly=False,
    )

    # === COMPUTE METHODS === #

    def _compute_sale_header_and_sale_footer_ids(self):
        for template in self:
            template.sale_header_ids = template.quotation_document_ids.filtered(
                lambda doc: doc.document_type == 'header'
            ).ids
            template.sale_footer_ids = template.quotation_document_ids.filtered(
                lambda doc: doc.document_type == 'footer'
            ).ids

    def _inverse_sale_header_and_sale_footer_ids(self):
        for template in self:
            quotation_documents = template.sale_header_ids + template.sale_footer_ids
            template.quotation_document_ids = quotation_documents.ids

    # === ACTION METHODS === #

    def action_open_dynamic_fields_configurator_wizard(self):
        self.ensure_one()
        valid_form_fields = set()
        for doc in self.quotation_document_ids:
            valid_form_fields.update(utils._get_valid_form_fields(doc.datas))
        default_form_fields = {'header_footer': list(valid_form_fields)}
        return {
            'name': _("Whitelist PDF Fields"),
            'type': 'ir.actions.act_window',
            'view_mode': 'form',
            'res_model': 'sale.pdf.quote.builder.dynamic.fields.wizard',
            'target': 'new',
            'context': {'default_current_form_fields': json.dumps(default_form_fields)},
        }
