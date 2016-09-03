from openerp import SUPERUSER_ID
import logging
from ...backend import prestashop
from ...unit.mapper import PrestashopImportMapper, mapping

_logger = logging.getLogger(__name__)

@prestashop
class TemplateMapper(PrestashopImportMapper):
    _model_name = 'prestashop.product.template'

    direct = [
        ('description', 'description_html'),
        ('description_short', 'description_short_html'),
        ('weight', 'weight'),
        ('wholesale_price', 'standard_price'),
        ('price', 'list_price'),
        ('id_shop_default', 'default_shop_id'),
        ('link_rewrite', 'link_rewrite'),
        ('reference', 'reference'),
        ('available_for_order', 'available_for_order'),
    ]

    @mapping
    def name(self, record):
        if record['name']:
            return {'name': record['name']}
        return {'name': 'noname'}

    @mapping
    def standard_price(self, record):
        if record['wholesale_price']:
            return {'standard_price': float(record['wholesale_price'])}
        return {}

    @mapping
    def list_price(self, record):
        taxes = self.taxes_id(record)
        if not record['price'] :
            _logger.debug("Price was not found in the record. Forced to 0")
            record['price'] = '0.0'
        
        prices_and_taxes = taxes
        prices_and_taxes.update({                    
                    'list_price_tax': float(record['price'])
                })
        
        tax_id = self.backend_record.tax_out_id.id
        
        if tax_id:
            tax_model = self.session.pool.get('account.tax')
            tax = tax_model.browse(
                self.session.cr,
                self.session.uid,
                tax_id,
            )
            _logger.debug("Price from record :%s and tax : %s ",record['price'],tax.amount)
            if not self.backend_record.taxes_included:
                prices_and_taxes.update({
                    'list_price': float(record['price']) / (1 + tax.amount),
                    'final_price': float(record['price']) / (1 + tax.amount),
                })
            else :
                prices_and_taxes.update({
                    'list_price': float(record['price']),
                    'final_price': float(record['price']),
                })
            
        elif record['price']:
            prices_and_taxes.update({
                'list_price': float(record['price']),                
                'final_price': float(record['price']),
            })
        return prices_and_taxes

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

    def _template_code_exists(self, code):
        model = self.session.pool.get('product.template')
        template_ids = model.search(self.session.cr, SUPERUSER_ID, [
            ('default_code', '=', code),
            ('company_id', '=', self.backend_record.company_id.id),
        ])
        return len(template_ids) > 0

    @mapping
    def default_code(self, record):
        """ Implements different strategies for default_code of the template """
        
        #_logger.debug('Use variant default code %s', self.backend_record.use_variant_default_code)
        if self.has_combinations(record)  :
            _logger.debug("has variant so skip the code", )
            return {}
        
        code = record.get('reference')
        if not code:
            code = "backend_%d_product_%s" % (
                self.backend_record.id, record['id']
            )
        if not self._template_code_exists(code):
            return {'default_code': code}
        i = 0
        current_code = '%s' % (code)
        return {'default_code': current_code}

    @mapping
    def descriptions(self, record):
        result = {}
        if record.get('description'):
            result['description_sale'] = record['description']
        if record.get('description_short'):
            result['description'] = record['description_short']
        return result

    @mapping
    def active(self, record):
        _logger.debug('Active of product_template')
        _logger.debug(bool(int(record['active'])))
        return {'always_available': bool(int(record['active']))}

    @mapping
    def sale_ok(self, record):
        return {'sale_ok': True}

    @mapping
    def purchase_ok(self, record):
        return {'purchase_ok': True}

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
        if self.has_combinations(record):
            return {}
        if record['ean13'] in ['', '0']:
            return {'ean13': False}
        
        barcode_nomenclature = self.env['barcode.nomenclature'].search([])[:1]
        if barcode_nomenclature.check_ean(record['ean13']):
            return {'ean13': record['ean13']}
        return {}


    @mapping
    def taxes_id(self, record):
        """
        Always return a tax when it's set in PS, 
        """
        tax_ids = []
        tax_ids.append(self.backend_record.tax_out_id.id)
        result = {"taxes_id": [(6, 0, tax_ids)]}
        return result


    @mapping
    def type(self, record):
        _logger.debug("Compute the product type : %s ", record['type']['value'])
        if record['type']['value'] and record['type']['value'] == 'virtual':
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

    @mapping
    def default_shop_id(self, record):
        shop_group_binder = self.binder_for('prestashop.shop.group')
        default_shop_id = shop_group_binder.to_openerp(
            record['id_shop_default'])
        if not default_shop_id:
            return {}
        return {'default_shop_id': default_shop_id}

    @mapping
    def product_brand_id(self, record):
        return {'product_brand_id': record['product_brand_id']}