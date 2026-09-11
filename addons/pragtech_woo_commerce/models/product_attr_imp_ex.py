# -*- coding: utf-8 -*-

from woocommerce import API
from odoo import fields, models, _
from odoo.exceptions import UserError
from odoo.tools import config
config['limit_time_real'] = 1000000

class ProductTemplateAttributeLine(models.Model):
    _inherit = 'product.template.attribute.line'

    woo_id = fields.Char('WooCommerce ID')
    is_exported = fields.Boolean('Exported')
    slug = fields.Char('Slug')

class ProductAttribute(models.Model):
    _inherit = 'product.attribute'

    woo_id = fields.Char('WooCommerce Id')
    is_exported = fields.Boolean('Synced In Woocommerce', default=False)
    slug = fields.Char('Slug')
    woo_instance_id = fields.Many2one('woo.instance')

    def cron_export_product_attr(self):
        all_instances = self.env['woo.instance'].sudo().search([])
        for rec in all_instances:
            if rec:
                self.env['product.attribute'].export_selected_attribute(rec)

    def export_selected_attribute(self, instance_id):
        location = instance_id.url
        cons_key = instance_id.client_id
        sec_key = instance_id.client_secret
        version = 'wc/v3'

        wcapi = API(url=location, consumer_key=cons_key, consumer_secret=sec_key, version=version)

        selected_ids = self.env.context.get('active_ids', [])
        selected_records = self.env['product.attribute'].sudo().browse(selected_ids)
        all_records = self.env['product.attribute'].sudo().search([])
        if selected_records:
            records = selected_records
        else:
            records = all_records

        list = []
        attr_val = []
        for rec in records:
            for val in rec.value_ids:
                attr_val.append({
                    'id': val.woo_id,
                    'name': val.name,
                    'slug': str(val.slug) if val.slug else '',
                    'description': str(val.description) if val.description else '',
                })

            list.append({
                'id': rec.woo_id,
                'name': rec.name,
                'slug': rec.slug if rec.slug else '',
            })

        if list:
            for data in list:
                if not data.get('id'):
                    wcapi.post("products/attributes", data).json()
                else:
                    if attr_val:
                        for rec in attr_val:
                            if rec:
                                if rec.get('id'):
                                    try:
                                        wcapi.post("products/attributes/%s/terms/%s" % (data.get('id'), rec.get('id')),
                                                   rec)
                                    except Exception as error:
                                        raise UserError(_("Please check your connection and try again"))
                                else:
                                    try:
                                        wcapi.post("products/attributes/%s/terms" % data.get('id'), rec).json()
                                    except Exception as error:
                                        raise UserError(_("Please check your connection and try again"))

                    wcapi.post("products/attributes/%s" % (data.get('id')), data).json()

        self.import_product_attribute(instance_id)

    def cron_import_product_attr(self):
        all_instances = self.env['woo.instance'].sudo().search([])
        for rec in all_instances:
            if rec:
                self.env['product.attribute'].import_product_attribute(rec)

    def import_product_attribute(self, instance_id):
        location = instance_id.url
        cons_key = instance_id.client_id
        sec_key = instance_id.client_secret
        version = 'wc/v3'
        page = 1

        wcapi = API(url=location, consumer_key=cons_key, consumer_secret=sec_key, version=version,timeout=250,stream=True,chunk_size=1024)
        url = "products/attributes"
        while page > 0:
            try:
                data = wcapi.get(url, params={'orderby': 'id', 'order': 'asc', 'per_page': 100, 'page': page})
                page += 1
            except Exception as error:
                raise UserError(_("Please check your connection and try again"))

            if data.status_code == 200 and data.content:
                parsed_data = data.json()
                if len(parsed_data) == 0:
                    page = 0
                if parsed_data:
                    for ele in parsed_data:
                        dict_e = {}
                        attribute = self.env['product.attribute'].sudo().search([('woo_id', '=', ele.get('id')), ('name', '=', ele.get('name'))], limit=1)
                        attribute_without_woo = self.env['product.attribute'].sudo().search([('woo_id', '=', False), ('name', '=', ele.get('name'))], limit=1)

                        dict_e['woo_instance_id'] = instance_id.id
                        dict_e['is_exported'] = True
                        if ele.get('name'):
                            dict_e['name'] = ele.get('name')
                        if ele.get('id'):
                            dict_e['woo_id'] = ele.get('id')
                            url = "products/attributes/%s/terms" % ele.get('id')
                            data = wcapi.get(url, params={'orderby': 'id', 'order': 'asc', 'per_page': 100, 'page': page})

                            if data.status_code == 200:
                                parsed_data = data.json()
                                if parsed_data:
                                    for value in parsed_data:
                                        dict_value = {}
                                        existing_value = self.env['product.attribute.value'].sudo().search(['|', ('woo_id', '=', value.get('id')), ('name', '=', value.get('name'))],limit=1)
                                        if value.get('name'):
                                            dict_value['name'] = value.get('name')
                                        if value.get('id'):
                                            dict_value['woo_id'] = value.get('id')
                                        if value.get('slug'):
                                            dict_value['slug'] = value.get('slug')
                                        if value.get('description'):
                                            dict_value['description'] = value.get('description')
                                        if attribute.id and not existing_value:
                                            dict_value['attribute_id'] = attribute.id
                                            self.env['product.attribute.value'].sudo().create(dict_value)
                                        elif existing_value:
                                            if value.get('name'):
                                                existing_value.name = value.get('name')
                                            if value.get('slug'):
                                                existing_value.slug = value.get('slug')
                                            if value.get('description'):
                                                existing_value.description = value.get('description')

                        if ele.get('slug'):
                            dict_e['slug'] = ele.get('slug')

                        if not attribute and attribute_without_woo:
                            attribute_without_woo.sudo().write(dict_e)

                        if attribute and not attribute_without_woo:
                            attribute.sudo().write(dict_e)

                        if not attribute and not attribute_without_woo:
                            self.env['product.attribute'].sudo().create(dict_e)
            else:
                page = 0

class ProductAttributeValue(models.Model):
    _inherit = 'product.attribute.value'

    woo_id = fields.Char('WooCommerce Id')
    is_exported = fields.Boolean('Synced In Woocommerce', default=False)
    slug = fields.Char('Slug')
    description = fields.Text('Description')
    woo_attr_val_description = fields.Html('Attribute Value Description')
    attribute_id = fields.Many2one('product.attribute', 'Attribute', required=1, copy=False)
    woo_instance_id = fields.Many2one('woo.instance', ondelete='cascade')

    def cron_import_product_attr_value(self):
        all_instances = self.env['woo.instance'].sudo().search([])
        for rec in all_instances:
            if rec:
                self.env['product.attribute.value'].import_product_attribute_term(rec)

    def import_product_attribute_term(self, instance_id):
        location = instance_id.url
        cons_key = instance_id.client_id
        sec_key = instance_id.client_secret
        version = 'wc/v3'

        wcapi = API(url=location, consumer_key=cons_key, consumer_secret=sec_key, version=version)
        imported_attr = self.env['product.attribute'].sudo().search([])
        for rec in imported_attr:
            page = 1
            if rec.woo_id:
                url = "products/attributes/%s/terms" % rec.woo_id
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
                        if parsed_data:
                            for value in parsed_data:
                                existing_attr_value = False
                                existing_attr_value = self.env['product.attribute.value'].sudo().search(['|', ('woo_id', '=', value.get('id')), ('name', '=', value.get('name')),('attribute_id','=',rec.id)], limit=1)

                                dict_value = {}
                                if value.get('name'):
                                    dict_value['name'] = value.get('name')
                                if rec.id:
                                    dict_value['attribute_id'] = rec.id

                                if value.get('description'):
                                    dict_value['description'] = value.get('description')
                                    dict_value['woo_attr_val_description'] = value.get('description')
                                if value.get('id'):
                                    dict_value['woo_id'] = value.get('id')
                                if value.get('slug'):
                                    dict_value['slug'] = value.get('slug')

                                dict_value['woo_instance_id'] = instance_id.id
                                dict_value['is_exported'] = True

                                if not existing_attr_value and dict_value['attribute_id']:
                                    self.env['product.attribute.value'].sudo().create(dict_value)

                                elif existing_attr_value:
                                    existing_attr_value.sudo().write(dict_value)
                    else:
                        page = 0

    def cron_export_product_attr_value(self):
        all_instances = self.env['woo.instance'].sudo().search([])
        for rec in all_instances:
            if rec:
                self.env['product.attribute.value'].export_selected_attribute_terms(rec)

    def export_selected_attribute_terms(self, instance_id):
        location = instance_id.url
        cons_key = instance_id.client_id
        sec_key = instance_id.client_secret
        version = 'wc/v3'

        wcapi = API(url=location, consumer_key=cons_key, consumer_secret=sec_key, version=version)

        selected_ids = self.env.context.get('active_ids', [])
        selected_records = self.env['product.attribute.value'].sudo().browse(selected_ids)
        all_records = self.env['product.attribute.value'].sudo().search([])
        if selected_records:
            records = selected_records
        else:
            records = all_records

        for rec in records:
            data = {
                'id': rec.woo_id,
                'name': rec.name,
                'slug': rec.slug if rec.slug else '',
                'description': str(rec.woo_attr_val_description) if rec.woo_attr_val_description else ''
            }

            value = self.env['product.attribute.value'].sudo().search([('name', '=', data.get('name'))], limit=1)
            if data.get('id'):
                try:
                    if value.attribute_id.woo_id:
                        wcapi.post("products/attributes/%s/terms/%s" % (value.attribute_id.woo_id, data.get('id')),
                                   data).json()
                    else:
                        self.env['bus.bus'].sendone((self._cr.dbname, 'res.partner', self.env.user.partner_id.id), {
                            'type': 'simple_notification', 'title': _("Sync your attribute"),
                            'message': _(
                                "The attribute %s  is not synced with WooCommerce") % value.attribute_id.name
                        })
                except Exception as error:
                    raise UserError(_("Please check your connection and try again"))
            else:
                try:
                    if value.attribute_id.woo_id:
                        parsed_data =wcapi.post("products/attributes/%s/terms" % value.attribute_id.woo_id, data).json()
                        if parsed_data:
                            rec.write({
                                'woo_id': parsed_data.get('id'),
                                'is_exported': True,
                                'woo_instance_id': instance_id.id,
                            })
                    else:
                        self.env['bus.bus'].sendone((self._cr.dbname, 'res.partner', self.env.user.partner_id.id), {
                            'type': 'simple_notification', 'title': _("Sync your attribute"),
                            'message': _(
                                "The attribute %s  is not synced with WooCommerce") % value.attribute_id.name
                        })
                except Exception as error:
                    raise UserError(_("Please check your connection and try again"))

        # self.import_product_attribute_term(instance_id)
