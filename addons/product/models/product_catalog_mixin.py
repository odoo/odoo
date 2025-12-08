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

    def _get_product_catalog_products_data(self, products):
        """ Returns a dict containing the products' data. Those data are for products that aren't in
        the record yet. For products already in the record, see `_get_product_catalog_lines_data`.

        For each product, we call `_get_product_catalog_product_data` that sets every individual product's data

        :param products: Recordset of `product.product`.
        :rtype: dict
        :return: A dict with the following structure:
            {
                'productId': int
                'quantity': float (optional)
                'productType': string
                'price': float
                'uomDisplayName': string
                'productUomDisplayName': string (optional)
                'code': string (optional)
                'readOnly': bool (optional)
            }
        """
        catalog_info = {}
        for product in products:
            catalog_info[product.id] = self._get_product_catalog_product_data(product)
        return catalog_info

    def _get_product_catalog_order_line_info(self, product_ids, child_field=False, **kwargs):
        """ Returns products information to be shown in the catalog.
        :param list product_ids: The products currently displayed in the product catalog, as a list
                                 of `product.product` ids.
        :param dict kwargs: additional values given for inherited models.
        :rtype: dict
        :return: A dict with the following structure:
            {
                'productId': int
                'quantity': float (optional)
                'productType': string
                'price': float
                'uomDisplayName': string
                'productUomDisplayName': string (optional)
                'code': string (optional)
                'readOnly': bool (optional)
            }
        """
        order_line_info = {}

        for product, record_lines in self._get_product_catalog_record_lines(product_ids, child_field=child_field, **kwargs).items():
            order_line_info[product.id] = {
               **record_lines._get_product_catalog_lines_data(parent_record=self, **kwargs),
               'productType': product.type,
               'code': product.code if product.code else '',
            }
            if not order_line_info[product.id]['uomDisplayName']:
                order_line_info[product.id]['uomDisplayName'] = product.uom_id.display_name

        default_data = self._default_order_line_values(child_field)
        products = self.env['product.product'].browse(product_ids)
        products_data = self._get_product_catalog_products_data(products)
        for product_id, data in products_data.items():
            if product_id in order_line_info:
                continue
            order_line_info[product_id] = {**default_data, **data}

        return order_line_info

    def _get_action_add_from_catalog_extra_context(self):
        return {
            'display_uom': self.env.user.has_group('uom.group_uom'),
            'product_catalog_order_id': self.id,
            'product_catalog_order_model': self._name,
        }

    def _is_readonly(self):
        """ Must be overrided by each model using this mixin.
        :return: Whether the record is read-only or not.
        :rtype: bool
        """
        return False

    def _update_order_line_info(self, product, quantity, uom=False, **kwargs):
        """ Update the line information for a given product or create a new one if none exists yet.
        Must be overrided by each model using this mixin.
        :param object product: The product, as a `product.product` instance.
        :param int quantity: The product's quantity.
        :param dict kwargs: additional values given for inherited models.
        :return: The unit price of the product, based on the pricelist of the
                 order and the quantity selected, the price per product unit
                 and the uom display name only if a line has been removed.
        :rtype: dict
        """
        return {'price': 0}

    def _get_product_catalog_price_and_data(self, product, **kwargs):
        """
            This function will return a dict containing the price of the product, UoM display name , and the seller's data if found.
            :param match_seller: Decide whether to try to match with a seller or not
            :param use_standard_price: Use standard price, if false list_price will be used for price.
            :param date: date of the order/invoice
            :param partner: partner set on the order/invoice
            :param order: order/invoice
            :rtype: dict
            :return: A dict with the following structure:
                {
                    'price': float,
                    'uomDisplayName': string,
                    'uomFactor': float (optional),
                    'productUomDisplayName': string (optional),
                    'productUnitPrice': float (optional)
                    'min_qty': float (optional)
                }
        """
        self.ensure_one()
        product.ensure_one()
        uom_id = kwargs.get('uom_id', False)
        product_infos = {
            'price': kwargs.get('price', product.standard_price),
            'uomDisplayName': (uom_id or product.uom_id).display_name,
            'uomId': (uom_id or product.uom_id).id,
        }
        match_seller = kwargs.get('match_seller', False)
        date = kwargs.get('date', False)
        # Check if there is a price and a minimum quantity for the order's vendor.
        if match_seller and hasattr(self, 'partner_id') and self.partner_id:
            seller = product._select_seller(
                partner_id=self.partner_id,
                quantity=None,
                date=date,
                uom_id=uom_id,
                ordered_by='min_qty',
                params={'order_id': self, 'force_uom': kwargs.get('force_uom', False)}
            )
            if seller:
                seller_price = seller.currency_id._convert(
                    from_amount=seller.price_discounted,
                    to_currency=product.currency_id,
                    company=product.company_id,
                    round=False
                )
                if seller.uom_id != product.uom_id:
                    product_infos.update(
                        uomFactor=seller.uom_id.factor / product.uom_id.factor,
                        productUomDisplayName=product.uom_id.display_name,
                        productUnitPrice=seller_price
                    )

                product_infos.update(
                    price=product.uom_id._compute_price(seller_price, seller.uom_id),
                    min_qty=seller.min_qty,
                    uomId=seller.uom_id.id,
                    uomDisplayName=seller.uom_id.display_name,
                )
        return product_infos

    def _get_product_catalog_product_data(self, product, **kwargs):
        """
            This function will return a dict containing all the product data.
            To be overriden in any module that needs to add extra arguments.
            :rtype: dict
            :return: A dict with the following structure:
                {
                    'productType': float,
                    'uomDisplayName': string,
                    'productUomDisplayName': string (optional),
                    'code': float (optional),
                    'kwargs': dict (optional)
                }
        """
        product_data = {
            'productType': product.type,
            'uomDisplayName': product.uom_id.display_name,
            'productUomDisplayName': product.uom_id.display_name,
            'code': product.code if product.code else '',
            **kwargs,
        }
        return product_data
