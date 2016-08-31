# -*- coding: utf-8 -*-
import datetime
import mimetypes
import json

from openerp import SUPERUSER_ID
from openerp.osv import fields, orm

# from addons.product import check_ean

from openerp.addons.connector.queue.job import job
from openerp.addons.connector.event import on_record_write
from openerp.addons.connector.unit.synchronizer import Exporter
from .unit.import_synchronizer import DelayedBatchImport
from .unit.import_synchronizer import PrestashopImportSynchronizer
from .unit.import_synchronizer import import_record
from openerp.addons.connector.unit.mapper import mapping

from prestapyt import PrestaShopWebServiceError

from .unit.backend_adapter import GenericAdapter, PrestaShopCRUDAdapter

from .connector import get_environment
from .unit.mapper import PrestashopImportMapper
from backend import prestashop

from prestapyt import PrestaShopWebServiceDict

try:
    from xml.etree import cElementTree as ElementTree
except ImportError, e:
    from xml.etree import ElementTree


########  product  ########
@prestashop
class ProductMapper(PrestashopImportMapper):
    _model_name = 'prestashop.product.product'

    direct = [
        ('description', 'description_html'),
        ('description_short', 'description_short_html'),
        ('weight', 'weight'),
        ('wholesale_price', 'standard_price'),
        ('price', 'list_price'),
        ('id_shop_default', 'default_shop_id'),
        ('link_rewrite', 'link_rewrite'),
        ('reference', 'reference'),
    ]

    @mapping
    def name(self, record):
        if record['name']:
            return {'name': record['name']}
        return {'name': 'noname'}

    @mapping
    def date_add(self, record):
        if record['date_add'] == '0000-00-00 00:00:00':
            return {'date_add': datetime.datetime.now()}
        return {'date_add': record['date_add']}

    @mapping
    def date_upd(self, record):
        if record['date_upd'] == '0000-00-00 00:00:00':
            return {'date_upd': datetime.datetime.now()}
        return {'date_upd': record['date_upd']}

    def has_combinations(self, record):
        combinations = record.get('associations', {}).get(
            'combinations', {}).get('combinations', [])
        return len(combinations) != 0

    def _product_code_exists(self, code):
        model = self.session.pool.get('product.product')
        product_ids = model.search(self.session.cr, SUPERUSER_ID, [
            ('default_code', '=', code),
            ('company_id', '=', self.backend_record.company_id.id),
        ])
        return len(product_ids) > 0

    @mapping
    def default_code(self, record):
        code = record.get('reference')
        if not code:
            code = "backend_%d_product_%s" % (
                self.backend_record.id, record['id']
            )
        if not self._product_code_exists(code):
            return {'default_code': code}
        i = 1
        current_code = '%s_%d' % (code, i)
        while self._product_code_exists(current_code):
            i += 1
            current_code = '%s_%d' % (code, i)
        return {'default_code': current_code}

    @mapping
    def product_brand_id(self, record):
        return {'product_brand_id': record['product_brand_id']}

    @mapping
    def active(self, record):
        return {'always_available': bool(int(record['active']))}

    @mapping
    def sale_ok(self, record):
        # if this product has combinations, we do not want to sell this product,
        # but its combinations (so sale_ok = False in that case).
        sale_ok = (record['available_for_order'] == '1')
        return {'sale_ok': sale_ok}

    @mapping
    def purchase_ok(self, record):
        return {'purchase_ok': not self.has_combinations(record)}

    @mapping
    def categ_id(self, record):
        return {'categ_id': self.backend_record.unrealized_product_category_id.id}

    @mapping
    def backend_id(self, record):
        return {'backend_id': self.backend_record.id}

    @mapping
    def company_id(self, record):
        return {'company_id': self.backend_record.company_id.id}

    @mapping
    def ean13(self, record):
        if record['ean13'] in ['', '0']:
            return {}
        # if check_ean(record['ean13']):
        #     return {'ean13': record['ean13']}
        return {}

    @mapping
    def taxes_id(self, record):
        return {"taxes_id": self.backend_record.tax_out_id.id}

    @mapping
    def type(self, record):
        # If the product has combinations, this main product is not a real
        # product. So it is set to a 'service' kind of product. Should better be
        # a 'virtual' product... but it does not exist...
        # The same if the product is a virtual one in prestashop.
        if ((record['type']['value'] and record['type']['value'] == 'virtual')
                or self.has_combinations(record)):
            return {"type": 'service'}
        return {"type": 'product'}

    @mapping
    def procure_method(self, record):
        if record['type'] == 'pack':
            return {
                'procure_method': 'make_to_order',
                'supply_method': 'produce',
            }
        return {}


@prestashop
class ProductAdapter(GenericAdapter):
    _model_name = 'prestashop.product.product'
    _prestashop_model = 'products'
    _export_node_name = 'product'


@prestashop
class ProductInventoryExport(Exporter):
    _model_name = ['prestashop.product.product']

    def get_filter(self, product):
        binder = self.binder_for()
        prestashop_id = binder.to_backend(product.id)
        return {
            'filter[id_product]': prestashop_id,
            'filter[id_product_attribute]': 0
        }

    def run(self, binding_id, fields):
        """ Export the product inventory to Prestashop """
        product = self.session.browse(self.model._name, binding_id)
        adapter = self.unit_for(
            GenericAdapter, '_import_stock_available'
        )
        filter = self.get_filter(product)
        adapter.export_quantity(filter, int(product.quantity))


@prestashop
class ProductInventoryBatchImport(DelayedBatchImport):
    _model_name = ['_import_stock_available']

    def run(self, filters=None, **kwargs):
        if filters is None:
            filters = {}
        filters['display'] = '[id_product,id_product_attribute]'
        return super(ProductInventoryBatchImport, self).run(filters, **kwargs)

    def _run_page(self, filters, **kwargs):
        records = self.backend_adapter.get(filters)
        for record in records['stock_availables']['stock_available']:
            self._import_record(record, **kwargs)
        return records['stock_availables']['stock_available']

    def _import_record(self, record, **kwargs):
        """ Delay the import of the records"""
        import_record.delay(
            self.session,
            '_import_stock_available',
            self.backend_record.id,
            record,
            **kwargs
        )


@prestashop
class ProductInventoryImport(PrestashopImportSynchronizer):
    _model_name = ['_import_stock_available']

    def _get_quantity(self, record):
        filters = {
            'filter[id_product]': record['id_product'],
            'filter[id_product_attribute]': record['id_product_attribute'],
            'display': '[quantity]',
        }
        quantities = self.backend_adapter.get(filters)
        all_qty = 0
        quantities = quantities['stock_availables']['stock_available']
        if isinstance(quantities, dict):
            quantities = [quantities]
        for quantity in quantities:
            all_qty += int(quantity['quantity'])
        return all_qty

    def _get_product(self, record):
        if record['id_product_attribute'] == '0':
            binder = self.binder_for('prestashop.product.product')
            return binder.to_openerp(record['id_product'], unwrap=True)
        binder = self.binder_for('prestashop.product.combination')
        return binder.to_openerp(record['id_product_attribute'], unwrap=True)

    def run(self, record):
        self._check_dependency(record['id_product'], 'prestashop.product.product')
        if record['id_product_attribute'] != '0':
            self._check_dependency(record['id_product_attribute'], 'prestashop.product.combination')

        qty = self._get_quantity(record)
        if qty < 0:
            qty = 0
        product_id = self._get_product(record)

        product_qty_obj = self.session.pool['stock.change.product.qty']
        vals = {
            'location_id': self.backend_record.warehouse_id.lot_stock_id.id,
            'product_id': product_id,
            'new_quantity': qty,
        }
        
        product_qty_id = self.session.create("stock.change.product.qty", vals)
        context = {'active_id': product_id}
        product_qty_obj.change_product_qty(
            self.session.cr,
            self.session.uid,
            [product_qty_id],
            context=context
        )


@prestashop
class ProductInventoryAdapter(GenericAdapter):
    _model_name = '_import_stock_available'
    _prestashop_model = 'stock_availables'
    _export_node_name = 'stock_available'

    def get(self, options=None):
        api = self.connect()
        return api.get(self._prestashop_model, options=options)

    def export_quantity(self, filters, quantity):
        self.export_quantity_url(
            self.backend_record.location,
            self.backend_record.webservice_key,
            filters,
            quantity
        )

        shop_ids = self.session.search('prestashop.shop', [
            ('backend_id', '=', self.backend_record.id),
            ('default_url', '!=', False),
        ])
        shops = self.session.browse('prestashop.shop', shop_ids)
        for shop in shops:
            self.export_quantity_url(
                '%s/api' % shop.default_url,
                self.backend_record.webservice_key,
                filters,
                quantity
            )

    def export_quantity_url(self, url, key, filters, quantity):
        api = PrestaShopWebServiceDict(url, key)
        response = api.search(self._prestashop_model, filters)
        for stock_id in response:
            res = api.get(self._prestashop_model, stock_id)
            first_key = res.keys()[0]
            stock = res[first_key]
            stock['quantity'] = int(quantity)
            try:
                api.edit(self._prestashop_model, {
                    self._export_node_name: stock
                })
            except ElementTree.ParseError:
                pass


# fields which should not trigger an export of the products
# but an export of their inventory
INVENTORY_FIELDS = ('quantity',)


@on_record_write(model_names=[
    'prestashop.product.product',
    'prestashop.product.combination'
])
def prestashop_product_stock_updated(session, model_name, record_id,
                                     fields=None):
    if session.context.get('connector_no_export'):
        return
    inventory_fields = list(set(fields).intersection(INVENTORY_FIELDS))
    if inventory_fields:
        export_inventory.delay(session, model_name,
                               record_id, fields=inventory_fields,
                               priority=20)


@job
def export_inventory(session, model_name, record_id, fields=None):
    """ Export the inventory configuration and quantity of a product. """
    product = session.browse(model_name, record_id)
    backend_id = product.backend_id.id
    env = get_environment(session, model_name, backend_id)
    inventory_exporter = env.get_connector_unit(ProductInventoryExport)
    return inventory_exporter.run(record_id, fields)

@job
def import_inventory(session, backend_id):
    env = get_environment(session, '_import_stock_available', backend_id)
    inventory_importer = env.get_connector_unit(ProductInventoryBatchImport)
    return inventory_importer.run()
