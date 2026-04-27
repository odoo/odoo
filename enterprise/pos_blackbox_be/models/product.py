# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, api
from odoo.exceptions import UserError
from odoo.tools.translate import _


class ProductProduct(models.Model):
    _inherit = "product.product"

    @api.model
    def set_tax_on_work_in_out(self):
        existing_companies = self.env["res.company"].sudo().search([])
        for company in existing_companies:
            if company.chart_template == "be_comp":
                tax_0 = self.env.ref(f'account.{company.id}_attn_VAT-OUT-00-L', raise_if_not_found=False)
                if tax_0:
                    if not tax_0.active:
                        tax_0.active = True
                    for work_product in self.env['pos.config']._get_work_products():
                        work_product.with_company(company.id).write({"taxes_id": [(4, tax_0.id)]})

    def _load_pos_data(self, data):
        response = super()._load_pos_data(data)
        if self.env.company.country_code == 'BE':
            work_products_ids = self.env['pos.config']._get_work_products().ids
            product_ids = [product['id'] for product in response['data']]
            ids_to_load = []
            for product in work_products_ids:
                if product not in product_ids:
                    ids_to_load.append(product)
            if len(ids_to_load):
                work_products = self.env['product.product'].search_read(
                    [('id', 'in', ids_to_load)],
                    response['fields'],
                    load=False
                )
                config_id = self.env['pos.config'].browse(data['pos.config']['data'][0]['id'])
                self._process_pos_ui_product_product(work_products, config_id)

                product_ids = [product['id'] for product in response['data']]
                for product in work_products:
                    if product['id'] not in product_ids:
                        response['data'].append(product)

        return response


class ProductTemplate(models.Model):
    _inherit = "product.template"

    @api.model_create_multi
    def create(self, vals_list):
        products = super().create(vals_list)
        for value in vals_list:
            self.env["pos_blackbox_be.log"].sudo().create([{
                "action": "create",
                "model_name": self._name,
                "record_name": value['name'],
                "description": "Product %s created" % value['name'],
            }])
        return products

    @api.ondelete(at_uninstall=False)
    def _unlink_if_workin_workout_deleted(self):
        restricted_product_ids = self.env['pos.config']._get_work_products().ids

        for product in self.ids:
            if product in restricted_product_ids:
                raise UserError(_("Deleting this product is not allowed."))

        for product in self:
            self.env["pos_blackbox_be.log"].sudo().create([{
                "action": "delete",
                "model_name": product._name,
                "record_name": product.name,
                "description": "Product %s deleted" % product.name,
            }])
