# -*- coding: utf-8 -*-

from woocommerce import API
from odoo import models, fields, _
from odoo.exceptions import UserError
from odoo.tools import config
config['limit_time_real'] = 1000000

class ProductTag(models.Model):
    _description = "Product Tag"
    _name = 'product.tag.woo'

    woo_id = fields.Char('WooCommerce ID')
    name = fields.Char('Tag name')
    slug = fields.Char('slug')
    description = fields.Html('Description')
    woo_instance_id = fields.Many2one('woo.instance', ondelete='cascade')
    is_exported = fields.Boolean('Synced In Woocommerce', default=False)

    def cron_import_product_tag(self):
        all_instances = self.env['woo.instance'].sudo().search([])
        for rec in all_instances:
            if rec:
                self.env['product.tag.woo'].import_product_tag(rec)

    def import_product_tag(self, instance_id):
        location = instance_id.url
        cons_key = instance_id.client_id
        sec_key = instance_id.client_secret
        version = 'wc/v3'
        page = 1

        wcapi = API(url=location,
                    consumer_key=cons_key,
                    consumer_secret=sec_key,
                    version=version
                    )
        url = "products/tags"
        while page > 0:
            try:
                data = wcapi.get(url, params={'per_page': 100, 'page': page})
                page += 1
            except Exception as error:
                raise UserError(_("Please check your connection and try again"))

            if data.status_code == 200 and data.content:
                parsed_data = data.json()
                if len(parsed_data) == 0:
                    page = 0
                for rec in parsed_data:
                    existing_tag = self.env['product.tag.woo'].sudo().search(
                        ['|', ('woo_id', '=', rec.get('id')), ('name', '=', rec.get('name'))], limit=1)
                    dict_value = {}
                    dict_value['woo_instance_id'] = instance_id.id
                    dict_value['is_exported'] = True
                    if rec.get('name'):
                        dict_value['name'] = rec.get('name')
                    if rec.get('id'):
                        dict_value['woo_id'] = rec.get('id')

                    if rec.get('description'):
                        dict_value['description'] = rec.get('description')

                    if rec.get('slug'):
                        dict_value['slug'] = rec.get('slug')

                    if existing_tag:
                        existing_tag.sudo().write(dict_value)
                    else:
                        self.env['product.tag.woo'].sudo().create(dict_value)
            else:
                page = 0

    def cron_export_product_tag(self):
        all_instances = self.env['woo.instance'].sudo().search([])
        for rec in all_instances:
            if rec:
                self.env['product.tag.woo'].export_selected_product_tag(rec)

    def export_selected_product_tag(self, instance_id):
        location = instance_id.url
        cons_key = instance_id.client_id
        sec_key = instance_id.client_secret
        version = 'wc/v3'

        wcapi = API(url=location,
                    consumer_key=cons_key,
                    consumer_secret=sec_key,
                    version=version
                    )

        selected_ids = self.env.context.get('active_ids', [])
        selected_records = self.env['product.tag.woo'].sudo().browse(selected_ids)
        all_records = self.env['product.tag.woo'].sudo().search([])
        if selected_records:
            records = selected_records
        else:
            records = all_records

        list = []
        for rec in records:
            data ={
                'id': rec.woo_id,
                'name': rec.name,
                'slug': rec.slug if rec.slug else '',
                'description': str(rec.description) if rec.description else ''
            }

            if data.get('id'):
                try:
                    wcapi.post("products/tags/%s" % data.get('id'), data)
                except Exception as error:
                    raise UserError(_("Please check your connection and try again"))
            else:
                try:
                    parsed_data = wcapi.post("products/tags", data).json()
                    if parsed_data:
                        rec.write({
                            'woo_id': parsed_data.get('id'),
                            'is_exported': True,
                            'woo_instance_id': instance_id.id,
                        })
                except Exception as error:
                    raise UserError(_("Please check your connection and try again"))

        # self.import_product_tag(instance_id)
