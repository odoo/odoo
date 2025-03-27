import logging

from odoo import models

_logger = logging.getLogger("===+++ Product Template +++===")


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    def woo_odoo_product_template_process(self, instance_id=None):
        """
        In this create mapping product with category, attribute, attribute value form odoo and
        if product is already mapped so update product
        :param instance_id: Browseable object of instance
        :return: Nothing
        """
        active_ids = self.env['product.template'].browse(self._context.get("active_ids"))
        for product_tmpl_id in active_ids:
            eg_product_tmpl_id = self.env['eg.product.template'].search(
                [('odoo_product_tmpl_id', '=', product_tmpl_id.id), ('instance_id', '=', instance_id.id)])
            if not eg_product_tmpl_id:
                woo_product_tmpl_obj = self.env['eg.product.template']

                for attribute_line_id in product_tmpl_id.attribute_line_ids:
                    eg_attribute_id = self.env['eg.product.attribute'].search(
                        [('name', '=', attribute_line_id.attribute_id.name), ('instance_id', '=', instance_id.id)])
                    if not eg_attribute_id:
                        eg_attribute_id = self.env['eg.product.attribute'].create(
                            {'name': attribute_line_id.attribute_id.name,
                             'odoo_attribute_id': attribute_line_id.attribute_id.id,
                             'instance_id': instance_id.id})
                        for value_id in attribute_line_id.value_ids:
                            self.env['eg.attribute.value'].create({'name': value_id.name,
                                                                   'instance_id': instance_id.id,
                                                                   'inst_attribute_id': eg_attribute_id.id,
                                                                   'odoo_attribute_value_id': value_id.id})
                    else:
                        for value_id in attribute_line_id.value_ids:
                            woo_attribute_terms_id = self.env['eg.attribute.value'].search(
                                [('name', '=', value_id.name), ('instance_id', '=', instance_id.id),
                                 ("inst_attribute_id", "=", eg_attribute_id.id)])  # Changes by Akash
                            if not woo_attribute_terms_id:
                                self.env['eg.attribute.value'].create({'name': value_id.name,
                                                                       'instance_id': instance_id.id,
                                                                       'inst_attribute_id': eg_attribute_id.id,
                                                                       'odoo_attribute_value_id': value_id.id})

                line_value_list = []
                product_attribute_value_ids = self.env['eg.attribute.value']
                for attribute_line_id in product_tmpl_id.attribute_line_ids:
                    eg_attribute_id = self.env['eg.product.attribute'].search(
                        [('odoo_attribute_id', '=', attribute_line_id.attribute_id.id),
                         ('instance_id', '=', instance_id.id)])

                    eg_value_ids = self.env['eg.attribute.value'].search(
                        [('odoo_attribute_value_id', 'in', attribute_line_id.value_ids.ids),
                         ('instance_id', '=', instance_id.id)])
                    print(product_attribute_value_ids)
                    line_value_list.append(
                        (0, 0, {'eg_product_attribute_id': eg_attribute_id.id,
                                'eg_value_ids': [(6, 0, eg_value_ids.ids)]}))
                eg_category_id = None
                eg_category_list = []
                if product_tmpl_id.categ_id:
                    odoo_category_id = product_tmpl_id.categ_id
                    eg_category_id = self.env["eg.product.category"].search(
                        [('odoo_category_id', '=', odoo_category_id.id), ("instance_id", "=", instance_id.id)])
                    if not eg_category_id:
                        eg_parent_category_id = None
                        if odoo_category_id.parent_id:
                            eg_parent_category_id = self.env["eg.product.category"].search(
                                [('odoo_category_id', '=', odoo_category_id.parent_id.id),
                                 ("instance_id", "=", instance_id.id)])
                        eg_category_id = self.env["eg.product.category"].create(
                            [{
                                'odoo_category_id': odoo_category_id.id,
                                'name': odoo_category_id.name,
                                'parent_id': eg_parent_category_id and eg_parent_category_id.instance_product_category_id or "",
                                'count': odoo_category_id.product_count,
                                'real_parent_id': eg_parent_category_id and eg_parent_category_id.id or None,
                                'instance_id': instance_id.id,
                            }])

                if eg_category_id:
                    eg_category_list.append(eg_category_id.id)
                eg_product_tmpl_id = woo_product_tmpl_obj.create([{'instance_id': instance_id.id,
                                                                   'odoo_product_tmpl_id': product_tmpl_id.id,
                                                                   "name": product_tmpl_id.name,
                                                                   "default_code": product_tmpl_id.default_code,
                                                                   "price": str(product_tmpl_id.list_price),
                                                                   "regular_price": str(
                                                                       product_tmpl_id.standard_price),
                                                                   "sale_ok": product_tmpl_id.sale_ok,
                                                                   'purchase_ok': product_tmpl_id.purchase_ok,
                                                                   'weight': str(product_tmpl_id.weight),
                                                                   'eg_attribute_line_ids': line_value_list,
                                                                   'status': instance_id.product_status,
                                                                   'catalog_visibility': instance_id.product_catalog_visibility,
                                                                   'tax_status': instance_id.product_tax_status,
                                                                   'backorders': instance_id.product_backorder,
                                                                   'update_required': True,
                                                                   'eg_category_ids': [(6, 0, eg_category_list)],
                                                                   'stock_status': product_tmpl_id.qty_available and 'instock' or 'outofstock'
                                                                   }])
                woo_product_product_obj = self.env['eg.product.product']
                for product_variant in product_tmpl_id.product_variant_ids:
                    eg_value_ids = self.env["eg.attribute.value"].search(
                        [("odoo_attribute_value_id", "in", product_variant.product_template_attribute_value_ids.ids),
                         ("instance_id", "=", instance_id.id)])
                    woo_product_product_obj.create({'name': product_tmpl_id.name,
                                                    'instance_id': instance_id.id,
                                                    'odoo_product_id': product_variant.id,
                                                    'description': product_variant.description,
                                                    'default_code': product_variant.default_code,
                                                    'price': product_variant.list_price,
                                                    'product_regular_price': product_variant.standard_price,
                                                    'on_sale': product_variant.sale_ok,
                                                    'qty_available': product_variant.qty_available,
                                                    'eg_value_ids': [(6, 0, eg_value_ids.ids)],
                                                    'eg_tmpl_id': eg_product_tmpl_id.id,
                                                    'status': instance_id.product_status,
                                                    'tax_status': instance_id.product_tax_status,
                                                    'eg_category_ids': [(6, 0, eg_category_list)],
                                                    'update_required': True,
                                                    'backorders': instance_id.product_backorder,
                                                    'stock_status': product_variant.qty_available and 'instock' or 'outofstock'
                                                    })

            else:
                eg_product_tmpl_id.write({"name": product_tmpl_id.name,
                                          "default_code": product_tmpl_id.default_code,
                                          "price": str(product_tmpl_id.list_price),
                                          "regular_price": str(
                                              product_tmpl_id.standard_price),
                                          "sale_ok": product_tmpl_id.sale_ok,
                                          'purchase_ok': product_tmpl_id.purchase_ok,
                                          'weight': str(product_tmpl_id.weight),
                                          'status': instance_id.product_status,
                                          'catalog_visibility': instance_id.product_catalog_visibility,
                                          'tax_status': instance_id.product_tax_status,
                                          'backorders': instance_id.product_backorder,
                                          'update_required': True,
                                          'stock_status': product_tmpl_id.qty_available and 'instock' or 'outofstock',
                                          })
                for eg_product_id in eg_product_tmpl_id.eg_product_ids:
                    product_variant = eg_product_id.odoo_product_id
                    eg_product_id.write({'name': product_tmpl_id.name,
                                         'description': product_variant.description,
                                         'default_code': product_variant.default_code,
                                         'price': product_variant.list_price,
                                         'product_regular_price': product_variant.standard_price,
                                         'on_sale': product_variant.sale_ok,
                                         'qty_available': product_variant.qty_available,
                                         'status': instance_id.product_status,
                                         'tax_status': instance_id.product_tax_status,
                                         'update_required': True,
                                         'backorders': instance_id.product_backorder,
                                         'stock_status': product_variant.qty_available and 'instock' or 'outofstock',
                                         })
