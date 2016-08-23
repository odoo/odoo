# -*- coding: utf-8 -*-

import base64
import logging
from prestapyt import PrestaShopWebServiceDict
from openerp.addons.connector.unit.backend_adapter import CRUDAdapter
from ..backend import prestashop

_logger = logging.getLogger(__name__)


class PrestaShopWebServiceImage(PrestaShopWebServiceDict):

    def get_image(self, resource, resource_id=None, image_id=None,
                  options=None):
        full_url = self._api_url + 'images/' + resource
        if resource_id is not None:
            full_url += "/%s" % (resource_id,)
            if image_id is not None:
                full_url += "/%s" % (image_id)
        if options is not None:
            self._validate_query_options(options)
            full_url += "?%s" % (self._options_to_querystring(options),)
        response = self._execute(full_url, 'GET')

        image_content = base64.b64encode(response.content)

        return {
            'type': response.headers['content-type'],
            'content': image_content,
            'id_' + resource[:-1]: resource_id,
            'id_image': image_id
        }


class PrestaShopLocation(object):

    def __init__(self, location, webservice_key):
        self.location = location
        self.webservice_key = webservice_key
        self.api_url = '%s/api' % location


class PrestaShopCRUDAdapter(CRUDAdapter):
    """ External Records Adapter for PrestaShop """

    def __init__(self, environment):
        """

        :param environment: current environment (backend, session, ...)
        :type environment: :py:class:`connector.connector.Environment`
        """
        super(PrestaShopCRUDAdapter, self).__init__(environment)
        self.prestashop = PrestaShopLocation(
            self.backend_record.location,
            self.backend_record.webservice_key
        )

    def search(self, filters=None):
        """ Search records according to some criterias
        and returns a list of ids """
        raise NotImplementedError

    def read(self, id, attributes=None):
        """ Returns the information of a record """
        raise NotImplementedError

    def search_read(self, filters=None):
        """ Search records according to some criterias
        and returns their information"""
        raise NotImplementedError

    def create(self, data):
        """ Create a record on the external system """
        raise NotImplementedError

    def write(self, id, data):
        """ Update records on the external system """
        raise NotImplementedError

    def delete(self, id):
        """ Delete a record on the external system """
        raise NotImplementedError


class GenericAdapter(PrestaShopCRUDAdapter):

    _model_name = None
    _prestashop_model = None

    def connect(self):
        return PrestaShopWebServiceDict(self.prestashop.api_url,
                                        self.prestashop.webservice_key)

    def search(self, filters=None):
        """ Search records according to some criterias
        and returns a list of ids

        :rtype: list
        """
        api = self.connect()
        return api.search(self._prestashop_model, filters)

    def read(self, id, attributes=None):
        """ Returns the information of a record

        :rtype: dict
        """
        #TODO rename attributes in something better
        api = self.connect()
        res = api.get(self._prestashop_model, id, options=attributes)
        first_key = res.keys()[0]
        return res[first_key]

    def create(self, attributes=None):
        """ Create a record on the external system """
        api = self.connect()
        return api.add(self._prestashop_model, {
            self._export_node_name: attributes
        })

    def write(self, id, attributes=None):
        """ Update records on the external system """
        api = self.connect()
        attributes['id'] = id
        return api.edit(self._prestashop_model, {
            self._export_node_name: attributes
        })

    def delete(self, ids):
        api = self.connect()
        """ Delete a record(s) on the external system """
        return api.delete(self._prestashop_model, ids)


@prestashop
class ShopGroupAdapter(GenericAdapter):
    _model_name = 'prestashop.shop.group'
    _prestashop_model = 'shop_groups'


@prestashop
class ShopAdapter(GenericAdapter):
    _model_name = 'prestashop.shop'
    _prestashop_model = 'shops'


@prestashop
class ResLangAdapter(GenericAdapter):
    _model_name = 'prestashop.res.lang'
    _prestashop_model = 'languages'


@prestashop
class ResCountryAdapter(GenericAdapter):
    _model_name = 'prestashop.res.country'
    _prestashop_model = 'countries'


@prestashop
class ResCurrencyAdapter(GenericAdapter):
    _model_name = 'prestashop.res.currency'
    _prestashop_model = 'currencies'


@prestashop
class AccountTaxAdapter(GenericAdapter):
    _model_name = 'prestashop.account.tax'
    _prestashop_model = 'taxes'


@prestashop
class PartnerCategoryAdapter(GenericAdapter):
    _model_name = 'prestashop.res.partner.category'
    _prestashop_model = 'groups'


@prestashop
class PartnerAdapter(GenericAdapter):
    _model_name = 'prestashop.res.partner'
    _prestashop_model = 'customers'


@prestashop
class PartnerAddressAdapter(GenericAdapter):
    _model_name = 'prestashop.address'
    _prestashop_model = 'addresses'


@prestashop
class ProductCategoryAdapter(GenericAdapter):
    _model_name = 'prestashop.product.category'
    _prestashop_model = 'categories'


# @prestashop
# class ProductImageAdapter(PrestaShopCRUDAdapter):
#     _model_name = 'prestashop.product.image'
#     _prestashop_image_model = 'products'

#     def read(self, product_id, image_id, options=None):
#         api = PrestaShopWebServiceImage(self.prestashop.api_url,
#                                         self.prestashop.webservice_key)
#         return api.get_image(
#             self._prestashop_image_model,
#             product_id,
#             image_id,
#             options=options
#         )

# @prestashop
# class SupplierImageAdapter(PrestaShopCRUDAdapter):
#     _model_name = 'prestashop.supplier.image'
#     _prestashop_image_model = 'suppliers'

#     def read(self, supplier_id, options=None):
#         api = PrestaShopWebServiceImage(self.prestashop.api_url,
#                                         self.prestashop.webservice_key)
#         res = api.get_image(
#             self._prestashop_image_model,
#             supplier_id,
#             options=options
#         )
#         return res['content']


@prestashop
class TaxGroupAdapter(GenericAdapter):
    _model_name = 'prestashop.account.tax.group'
    _prestashop_model = 'tax_rule_groups'


@prestashop
class OrderPaymentAdapter(GenericAdapter):
    _model_name = '__not_exist_prestashop.payment'
    _prestashop_model = 'order_payments'


@prestashop
class OrderDiscountAdapter(GenericAdapter):
    _model_name = 'prestashop.sale.order.line.discount'
    _prestashop_model = 'order_discounts'


@prestashop
class SupplierAdapter(GenericAdapter):
    _model_name = 'prestashop.supplier'
    _prestashop_model = 'suppliers'


@prestashop
class SupplierInfoAdapter(GenericAdapter):
    _model_name = 'prestashop.product.supplierinfo'
    _prestashop_model = 'product_suppliers'

@prestashop
class MailMessageAdapter(GenericAdapter):
    _model_name = 'prestashop.mail.message'
    _prestashop_model = 'messages'


# @prestashop
# class BundleAdapter(GenericAdapter):
#     _model_name = ['prestashop.mrp.bom', 'prestashop.combination.mrp.bom']
#     _prestashop_model = 'products'


@prestashop
class PricelistAdapter(GenericAdapter):
    _model_name = 'prestashop.groups.pricelist'
    _prestashop_model = 'groups'
