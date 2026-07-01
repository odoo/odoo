# -*- coding: utf-8 -*-

from woocommerce import API
from odoo import fields, models, _
from odoo.exceptions import UserError
from odoo.tools import config

config['limit_time_real'] = 1000000


class ProductCategory(models.Model):
    _inherit = "product.category"
    _order = 'woo_id'

    woo_id = fields.Char('WooCommerce ID')
    slug = fields.Char('Slug')
    description = fields.Text(string='Description', translate=True)
    woo_category_description = fields.Html(string="Category Description", translate=True)
    woo_instance_id = fields.Many2one('woo.instance', ondelete='cascade')
    is_exported = fields.Boolean('Synced In Woocommerce', default=False)

    def cron_export_product_categ(self):
        all_instances = self.env['woo.instance'].sudo().search([])
        for rec in all_instances:
            if rec:
                self.env['product.category'].export_selected_category(rec)

    def export_selected_category(self, instance_id):
        location = instance_id.url
        cons_key = instance_id.client_id
        sec_key = instance_id.client_secret
        version = 'wc/v3'

        wcapi = API(url=location, consumer_key=cons_key, consumer_secret=sec_key, version=version)

        selected_ids = self.env.context.get('active_ids', [])
        selected_records = self.env['product.category'].sudo().browse(selected_ids)
        all_records = self.env['product.category'].sudo().search([])
        if selected_records:
            records = selected_records
        else:
            records = all_records

        for rec in records:
            data = {
                'id': rec.woo_id,
                'name': rec.name,
                'parent': int(rec.parent_id.woo_id),
                'description': str(rec.woo_category_description) if rec.woo_category_description else '',
                'slug': rec.slug if rec.slug else '',
            }
            if data.get('id'):
                try:
                    wcapi.post("products/categories/%s" % data.get('id'), data).json()
                except Exception as error:
                    raise UserError(_("Please check your connection and try again"))
            else:
                try:
                    parsed_data = wcapi.post("products/categories", data).json()
                    if parsed_data:
                        rec.write({
                            'woo_id': parsed_data.get('id'),
                            'is_exported': True,
                            'woo_instance_id': instance_id.id,
                        })
                except Exception as error:
                    raise UserError(_("Please check your connection and try again"))

        # self.import_product_category(instance_id)

    def cron_import_product_categ(self):
        all_instances = self.env['woo.instance'].sudo().search([])
        for rec in all_instances:
            if rec:
                self.env['product.category'].import_product_category(rec)

    def import_product_category(self, instance_id):
        location = instance_id.url
        cons_key = instance_id.client_id
        sec_key = instance_id.client_secret
        version = 'wc/v3'
        page = 1

        wcapi = API(url=location, consumer_key=cons_key, consumer_secret=sec_key, version=version)
        url = "products/categories"
        while page > 0:
            try:
                data = wcapi.get(url, params={'per_page': 100, 'page': page})
                page += 1
            except Exception as error:
                raise UserError(_("Please check your connection and try again"))

            if data.status_code == 200 and data.content:
                data = data.json()
                parsed_data = self.sort_product_categ(data)
                if len(parsed_data['product_categories']) == 0:
                    page = 0
                if parsed_data:
                    if parsed_data.get('product_categories'):
                        flag = False
                        for category in parsed_data.get('product_categories'):
                            # ''' This will avoid duplications'''
                            product_category = self.env['product.category'].sudo().search(
                                [('woo_id', '=', category.get('id'))],
                                limit=1)
                            dict_e = {}
                            ''' This is used to update woo_id of a product category, this
                            will avoid duplication of product while syncing product category.
                            '''
                            product_category_without_woo_id = self.env['product.category'].sudo().search(
                                [('woo_id', '=', False), ('name', '=', category.get('name'))], limit=1)
                            dict_e['woo_instance_id'] = instance_id.id
                            dict_e['is_exported'] = True
                            if category.get('name'):
                                dict_e['name'] = category.get('name')
                            if category.get('id'):
                                dict_e['woo_id'] = category.get('id')
                            if category.get('parent'):
                                parent = self.env['product.category'].sudo().search(
                                    [('woo_id', '=', category.get('parent'))],
                                    limit=1)
                                dict_e['parent_id'] = parent.id
                            if category.get('description'):
                                dict_e['description'] = category.get('description')
                                dict_e['woo_category_description'] = category.get('description')
                            if category.get('slug'):
                                dict_e['slug'] = category.get('slug')

                            if not product_category and product_category_without_woo_id:
                                product_category_without_woo_id.sudo().write(dict_e)

                            if product_category and not product_category_without_woo_id:
                                product_category.sudo().write(dict_e)

                            if not product_category and not product_category_without_woo_id:
                                self.env['product.category'].sudo().create(dict_e)
                            self.env.cr.commit()
            else:
                page = 0

    def sort_product_categ(self, woo_data):
        sortedlist = sorted(woo_data, key=lambda elem: "%02d" % (elem['id']))
        parsed_data = {'product_categories': sortedlist}
        return parsed_data
