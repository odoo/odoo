from unidecode import unidecode
import json

from openerp import SUPERUSER_ID
from openerp.osv import fields, orm
from backend import prestashop
from .unit.backend_adapter import GenericAdapter
from .unit.import_synchronizer import PrestashopImportSynchronizer
from .unit.import_synchronizer import TranslatableRecordImport
from .unit.import_synchronizer import import_batch
from .unit.mapper import PrestashopImportMapper
from .unit.import_synchronizer import import_record
from openerp.addons.connector.unit.backend_adapter import BackendAdapter
from openerp.addons.connector.unit.mapper import mapping
from openerp.osv.orm import browse_record_list

# from openerp.addons.product.product import check_ean

from .product import ProductInventoryExport

from prestapyt import PrestaShopWebServiceError

try:
    from xml.etree import cElementTree as ElementTree
except ImportError, e:
    from xml.etree import ElementTree


@prestashop
class ProductCombinationAdapter(GenericAdapter):
    _model_name = 'prestashop.product.combination'
    _prestashop_model = 'combinations'


@prestashop
class ProductCombinationRecordImport(PrestashopImportSynchronizer):
    _model_name = 'prestashop.product.combination'

    def _import_dependencies(self):
        record = self.prestashop_record
        option_values = record.get('associations', {}).get(
            'product_option_values', {}).get('product_option_value', [])
        if not isinstance(option_values, list):
            option_values = [option_values]
        backend_adapter = self.unit_for(
            BackendAdapter,
            'prestashop.product.combination.option.value'
        )
        for option_value in option_values:
            option_value = backend_adapter.read(option_value['id'])
            self._check_dependency(
                option_value['id_attribute_group'],
                'prestashop.product.combination.option',
            )
            self._check_dependency(
                option_value['id'],
                'prestashop.product.combination.option.value'
            )

            self.check_location(option_value)

    def check_location(self, option_value):
        option_binder = self.binder_for(
            'prestashop.product.combination.option')
        attribute_id = option_binder.to_openerp(
            option_value['id_attribute_group'], unwrap=True)
        product = self.mapper.main_product(self.prestashop_record)
        attribute_group_id = product.attribute_set_id.attribute_group_ids[0].id

        attribute_location_ids = self.session.search(
            'attribute.location',
            [
                ('attribute_id', '=', attribute_id),
                ('attribute_group_id', '=', attribute_group_id)
            ]
        )
        if not attribute_location_ids:
            self.session.create(
                'attribute.location',
                {
                    'attribute_id': attribute_id,
                    'attribute_group_id': attribute_group_id,
                }
            )

    def _after_import(self, erp_id):
        record = self.prestashop_record
        self.import_supplierinfo(erp_id, record['id_product'], record['id'])
        # self.import_bundle()

    def import_supplierinfo(self, erp_id, ps_product_id, ps_combination_id):
        filters = {
            'filter[id_product]': ps_product_id,
            'filter[id_product_attribute]': ps_combination_id,
        }
        import_batch(
            self.session,
            'prestashop.product.supplierinfo',
            self.backend_record.id,
            filters=filters
        )
        product = self.session.browse(
            'prestashop.product.combination', erp_id
        )
        ps_supplierinfo_ids = self.session.search(
            'prestashop.product.supplierinfo',
            [('product_id', '=', product.openerp_id.id)]
        )
        ps_supplierinfos = self.session.browse(
            'prestashop.product.supplierinfo', ps_supplierinfo_ids
        )
        for ps_supplierinfo in ps_supplierinfos:
            try:
                ps_supplierinfo.resync()
            except PrestaShopWebServiceError:
                ps_supplierinfo.openerp_id.unlink()


@prestashop
class ProductCombinationMapper(PrestashopImportMapper):
    _model_name = 'prestashop.product.combination'

    direct = [
        ('weight', 'weight'),
        ('reference', 'reference'),
    ]

    from_main = [
        'categ_id',
        'categ_ids',
        'taxes_id',
        'company_id',
        # 'image_medium',
    ]

    @mapping
    def price(self, record):
        main_product = self.main_product(record)
        if self.backend_record.taxes_included:
            price = main_product.list_price_tax_inc + float(record['unit_price_impact'])
            return {'list_price_tax_inc': price}
        price = main_product.list_price + float(record['unit_price_impact'])
        return {'list_price': price}

    @mapping
    def standard_price(self, record):
        price = float(record['wholesale_price'])
        if price == 0.0:
            main_product = self.main_product(record)
            price = main_product.standard_price
        return {'standard_price': price}

    @mapping
    def type(self, record):
        return {'type': 'product'}

    @mapping
    def from_main_product(self, record):
        main_product = self.main_product(record)
        result = {}
        for attribute in self.from_main:
            if attribute not in main_product:
                continue
            if hasattr(main_product[attribute], 'id'):
                result[attribute] = main_product[attribute].id
            elif type(main_product[attribute]) is browse_record_list:
                ids = []
                for element in main_product[attribute]:
                    ids.append(element.id)
                result[attribute] = [(6, 0, ids)]
            else:
                result[attribute] = main_product[attribute]
        return result

    def main_product(self, record):
        if hasattr(self, '_main_product'):
            return self._main_product
        product_id = self.get_main_product_id(record)
        self._main_product = self.session.browse(
            'prestashop.product.product',
            product_id
        )
        return self._main_product

    def get_main_product_id(self, record):
        product_binder = self.binder_for(
            'prestashop.product.product')
        return product_binder.to_openerp(record['id_product'])

    @mapping
    def attribute_set_id(self, record):
        product = self.main_product(record)
        if 'attribute_set_id' in product:
            return {'attribute_set_id': product.attribute_set_id.id}
        return {}

    def _get_option_value(self, record):
        option_values = record['associations']['product_option_values'][
            'product_option_value']
        if type(option_values) is dict:
            option_values = [option_values]

        for option_value in option_values:

            option_value_binder = self.binder_for(
                'prestashop.product.combination.option.value')
            option_value_openerp_id = option_value_binder.to_openerp(
                option_value['id'])

            option_value_object = self.session.browse(
                'prestashop.product.combination.option.value',
                option_value_openerp_id
            )
            yield option_value_object

    @mapping
    def name(self, record):
        product = self.main_product(record)
        options = []
        for option_value_object in self._get_option_value(record):
            key = option_value_object.attribute_id.field_description
            value = option_value_object.name
            options.append('%s:%s' % (key, value))
        return {'name': '%s (%s)' % (product.name, ' ; '.join(options))}

    @mapping
    def attributes_values(self, record):
        results = {}
        for option_value_object in self._get_option_value(record):
            field_name = option_value_object.attribute_id.name
            results[field_name] = option_value_object.id
        return results

    @mapping
    def main_product_id(self, record):
        return {'main_product_id': self.get_main_product_id(record)}

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
            code = "backend_%d_product_%s_combination_%s" % (
                self.backend_record.id, record['id_product'], record['id']
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
    def backend_id(self, record):
        return {'backend_id': self.backend_record.id}

    @mapping
    def ean13(self, record):
        if record['ean13'] in ['', '0']:
            return {}
        # if check_ean(record['ean13']):
        #     return {'ean13': record['ean13']}
        return {}


@prestashop
class ProductCombinationOptionAdapter(GenericAdapter):
    _model_name = 'prestashop.product.combination.option'
    _prestashop_model = 'product_options'


@prestashop
class ProductCombinationOptionRecordImport(PrestashopImportSynchronizer):
    _model_name = 'prestashop.product.combination.option'

    def _import_values(self):
        record = self.prestashop_record
        option_values = record.get('associations', {}).get(
            'product_option_values', {}).get('product_option_value', [])
        if not isinstance(option_values, list):
            option_values = [option_values]
        for option_value in option_values:
            self._check_dependency(
                option_value['id'],
                'prestashop.product.combination.option.value'
            )

    def run(self, ext_id):
        self.prestashop_id = ext_id
        self.prestashop_record = self._get_prestashop_data()
        field_name = self.mapper.name(self.prestashop_record)['name']
        if len(attribute_ids) == 0:
            # if we don't find it, we create a prestashop_product_combination
            super(ProductCombinationOptionRecordImport, self).run(ext_id)
        else:
            # else, we create only a prestashop.product.combination.option
            context = self._context()
            data = {
                'openerp_id': attribute_ids[0],
                'backend_id': self.backend_record.id,
            }
            erp_id = self.model.create(self.session.cr, self.session.uid, data, context)
            self.binder.bind(self.prestashop_id, erp_id)

        self._import_values()


@prestashop
class ProductCombinationOptionMapper(PrestashopImportMapper):
    _model_name = 'prestashop.product.combination.option'

    @mapping
    def attribute_type(self, record):
        return {'attribute_type': 'select'}

    @mapping
    def model_id(self, record):
        ids = self.session.search('ir.model',
                                  [('model', '=', 'product.product')])
        assert len(ids) == 1
        return {'model_id': ids[0], 'model': 'product.product'}

    @mapping
    def backend_id(self, record):
        return {'backend_id': self.backend_record.id}

    @mapping
    def name(self, record):
        name = None
        if 'language' in record['name']:
            language_binder = self.binder_for('prestashop.res.lang')
            languages = record['name']['language']
            if not isinstance(languages, list):
                languages = [languages]
            for lang in languages:
                erp_language_id = language_binder.to_openerp(
                    lang['attrs']['id'])
                if not erp_language_id:
                    continue
                erp_lang = self.session.read(
                    'prestashop.res.lang',
                    erp_language_id,
                    []
                )
                if erp_lang['code'] == 'en_US':
                    name = lang['value']
                    break
            if name is None:
                name = languages[0]['value']
        else:
            name = record['name']
        field_name = 'x_' + unidecode(name.replace(' ', ''))
        return {'name': field_name, 'field_description': name}


@prestashop
class ProductCombinationOptionValueAdapter(GenericAdapter):
    _model_name = 'prestashop.product.combination.option.value'
    _prestashop_model = 'product_option_values'


@prestashop
class ProductCombinationOptionValueRecordImport(TranslatableRecordImport):
    _model_name = 'prestashop.product.combination.option.value'

    _translatable_fields = {
        'prestashop.product.combination.option.value': ['name'],
    }


@prestashop
class ProductCombinationOptionValueMapper(PrestashopImportMapper):
    _model_name = 'prestashop.product.combination.option.value'

    direct = [
        ('name', 'name'),
        ('position', 'sequence'),
    ]

    @mapping
    def attribute_id(self, record):
        binder = self.binder_for(
            'prestashop.product.combination.option')
        attribute_id = binder.to_openerp(record['id_attribute_group'],
                                         unwrap=True)
        return {'attribute_id': attribute_id}

    @mapping
    def backend_id(self, record):
        return {'backend_id': self.backend_record.id}


@prestashop
class CombinationInventoryExport(ProductInventoryExport):
    _model_name = ['prestashop.product.combination']

    def get_filter(self, product):
        return {
            'filter[id_product]': product.main_product_id.prestashop_id,
            'filter[id_product_attribute]': product.prestashop_id,
        }
