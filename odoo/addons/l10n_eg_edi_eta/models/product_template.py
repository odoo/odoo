# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.


from odoo import api, fields, models


class ProductTemplate(models.Model):
    _inherit = "product.template"

    l10n_eg_eta_code = fields.Char('ETA Item code', compute='_compute_l10n_eg_eta_code',
                                   inverse='_set_l10n_eg_eta_code',
                                   help="This can be an EGS or GS1 product code, which is needed for the e-invoice.  "
                                        "The best practice however is to use that code also as barcode and in that case, "
                                        "you should put it in the Barcode field instead and leave this field empty.")

    @api.depends('product_variant_ids.l10n_eg_eta_code')
    def _compute_l10n_eg_eta_code(self):
        self.l10n_eg_eta_code = False
        for template in self:
            if len(template.product_variant_ids) == 1:
                template.l10n_eg_eta_code = template.product_variant_ids.l10n_eg_eta_code

    def _set_l10n_eg_eta_code(self):
        if len(self.product_variant_ids) == 1:
            self.product_variant_ids.l10n_eg_eta_code = self.l10n_eg_eta_code

    @api.model_create_multi
    def create(self, vals_list):
        templates = super().create(vals_list)

        for template, vals in zip(templates, vals_list):
            related_vals = {}
            if vals.get('l10n_eg_eta_code'):
                related_vals['l10n_eg_eta_code'] = vals['l10n_eg_eta_code']
            if related_vals:
                template.write(related_vals)

        return templates


class ProductProduct(models.Model):
    _inherit = "product.product"

    l10n_eg_eta_code = fields.Char('ETA Code', copy=False,
                                   help="This can be an EGS or GS1 product code, which is needed for the e-invoice.  "
                                        "The best practice however is to use that code also as barcode and in that case, "
                                        "you should put it in the Barcode field instead and leave this field empty. ")
