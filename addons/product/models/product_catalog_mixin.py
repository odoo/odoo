# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import _, api, models
from odoo.fields import Domain


class ProductCatalogMixin(models.AbstractModel):
    """ This mixin should be inherited when the model should be able to work
    with the product catalog.
    It assumes the model using this mixin has a O2M field where the products are added/removed and
    this field's co-related model should has a method named `_get_product_catalog_lines_data`.
    """
    _name = 'product.catalog.mixin'
    _description = 'Product Catalog Mixin'

    @api.readonly
    def action_add_from_catalog(self):
        kanban_view_id = self.env.ref('product.product_view_kanban_catalog').id
        search_view_id = self.env.ref('product.product_view_search_catalog').id
        additional_context = self._get_action_add_from_catalog_extra_context()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Products'),
            'res_model': 'product.product',
            'views': [(kanban_view_id, 'kanban'), (False, 'form')],
            'search_view_id': [search_view_id, 'search'],
            'domain': self._get_product_catalog_domain(),
            'context': {**self.env.context, **additional_context},
        }

    def _default_order_line_values(self, child_field=False):
        return {
            'quantity': 0,
            'readOnly': self._is_readonly() if self else False,
        }

    def _get_product_catalog_domain(self) -> Domain:
        """Get the domain to search for products in the catalog.

        For a model that uses products that has to be hidden in the catalog, it
        must override this method and extend the appropriate domain.
        :returns: A domain.
        """
        return (
            Domain('company_id', '=', False) | Domain('company_id', 'parent_of', self.company_id.id)
         ) & Domain('type', '!=', 'combo')

    def _get_product_catalog_record_lines(self, product_ids, **kwargs):
        """ Returns the record's lines grouped by product.
        Must be overrided by each model using this mixin.

        :param list product_ids: The ids of the products currently displayed in the product catalog.
        :rtype: dict
        """
        return {}

    def _get_product_catalog_order_data(self, products, **kwargs):
        """ Returns a dict containing the products' data. This is for products that aren't in
        the record yet. For products already in the record, see `_get_product_catalog_lines_data`.

        For each product, we call `_get_product_catalog_product_data` that sets every individual product's data

        :param products: Recordset of `product.product`.
        :rtype: dict
        """
        return {
            product.id: self._get_product_catalog_product_data(product, **kwargs)
            for product in products
        }

    def _get_product_catalog_order_line_info(self, product_ids, child_field=False, **kwargs):
        """ Returns products information to be shown in the catalog.
        :param list product_ids: The products currently displayed in the product catalog, as a list
                                 of `product.product` ids.
        :param dict kwargs: additional values given for inherited models.
        :rtype: dict
        """
        order_line_info = {}

        for product, record_lines in self._get_product_catalog_record_lines(product_ids, child_field=child_field, **kwargs).items():
            order_line_info[product.id] = {
               **record_lines._get_product_catalog_lines_data(parent_record=self, **kwargs),
               'productType': product.type,
               'code': product.code if product.code else '',
            }
            if self.env['res.groups']._is_feature_enabled('uom.group_uom') and not order_line_info[product.id]['uomDisplayName']:
                order_line_info[product.id]['uomDisplayName'] = product.uom_id.display_name

        default_data = self._default_order_line_values(child_field)
        products = self.env['product.product'].browse(product_ids)
        products_data = self._get_product_catalog_order_data(products, **kwargs)

        for product_id, data in products_data.items():
            if product_id in order_line_info:
                continue
            order_line_info[product_id] = {**default_data, **data}
        return order_line_info

    def _get_action_add_from_catalog_extra_context(self):
        return {
            'product_catalog_order_id': self.id,
            'product_catalog_order_model': self._name,
        }

    def _is_readonly(self):
        """ Must be overrided by each model using this mixin.
        :return: Whether the record is read-only or not.
        :rtype: bool
        """
        return False

    def _update_order_line_info(self, product, quantity, uom, **kwargs):
        """ Update the line information for a given product or create a new one if none exists yet.
        Must be overrided by each model using this mixin.
        :param object product: Recordset of `product.product`.
        :param int quantity: The product's quantity.
        :param int uom: Recordset of `uom.uom`.
        :param dict kwargs: additional values given for inherited models.
        :return: The unit price of the product, based on the pricelist of the
                 order and the quantity selected.
        :rtype: float
        """
        return 0.0

    def _get_product_catalog_product_data(self, product, **kwargs):
        """ This function is called within `_get_product_catalog_order_data` to return a dict
        with all the product's info needed for the catalog.
        :rtype: dict
        """
        return {
            'productType': product.type,
            'price': product.standard_price,
            'code': product.code if product.code else '',
            **self._get_product_catalog_uom_data(product, product.uom_id)
        }

    def _get_product_catalog_uom_data(self, product, uom):
        res = {
            'uomId': uom.id,
        }
        if not self.env['res.groups']._is_feature_enabled('uom.group_uom'):
            return res

        res.update({
            'uomDisplayName': uom.display_name,
            'productUomFactor': product.uom_id.factor / uom.factor,
            'productUomDisplayName': product.uom_id.display_name,
        })
        return res
