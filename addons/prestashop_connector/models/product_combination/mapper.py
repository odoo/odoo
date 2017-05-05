import logging

from ...unit.backend_adapter import GenericAdapter
from ...backend import prestashop
from ...unit.mapper import PrestashopImportMapper, mapping

from openerp.osv.orm import browse_record_list

_logger = logging.getLogger(__name__)

@prestashop
class ProductCombinationMapper(PrestashopImportMapper):
    _model_name = 'prestashop.product.combination'

    direct = []

    from_main = []

    @mapping
    def default_on(self, record):
        return {'default_on': bool(int(record['default_on']))}
    
    @mapping
    def type(self, record):
        main_template = self.main_template(record)
        return {'type':main_template['type']}
    
    @mapping
    def product_tmpl_id(self, record):
        template = self.main_template(record)
        return {'product_tmpl_id': template.openerp_id.id}
    
    @mapping
    def list_price(self, record):
        main_template = self.main_template(record)
        prices_and_taxes = {'list_price' : main_template['list_price']}
        prices_and_taxes.update({
                    "taxes_id": [(6, 0, [t.id for t in main_template['taxes_id']])]
                    })
                    
        _logger.debug(prices_and_taxes)
        _logger.debug(main_template['taxes_id'])
        return prices_and_taxes

    @mapping
    def categ_id(self, record):
        main_template = self.main_template(record)
        return {'categ_id' : main_template['categ_id'].id}
            
    @mapping
    def from_main_template(self, record):        
        main_template = self.main_template(record)
        result = {}           
        for attribute in record:
            _logger.debug("Attribute from product to be mapped : %s ", attribute)
            if attribute not in main_template:
                continue                
            if attribute == 'ean13' :
                # DOn't map the ean13 because of product_attribute
                # EAN13 and default code displayed on template are now those
                # of the default_on product
                _logger.debug("Attribute ean 13 from product won't be mapped from template")
                continue                
            if hasattr(main_template[attribute], 'id'):
                result[attribute] = main_template[attribute].id
            elif type(main_template[attribute]) is browse_record_list:
                ids = []
                for element in main_template[attribute]:
                    ids.append(element.id)
                result[attribute] = [(6, 0, ids)]
            else:
                result[attribute] = main_template[attribute]            
        return result

    def main_template(self, record):
        if hasattr(self, '_main_template'):
            return self._main_template
        template_id = self.get_main_template_id(record)
        self._main_template = self.env['prestashop.product.template'].browse(template_id)
        return self._main_template

    def get_main_template_id(self, record):
        template_binder = self.binder_for('prestashop.product.template')
        return template_binder.to_openerp(record['id_product'])

    def _get_option_value(self, record):
        option_values = record['associations']['product_option_values'][
            'product_option_values']
        if type(option_values) is dict:
            option_values = [option_values]

        for option_value in option_values:
            option_value_binder = self.binder_for('prestashop.product.attribute.value')
            option_value_openerp_id = option_value_binder.to_openerp(option_value['id'])
            option_value_object = self.env['prestashop.product.attribute.value'].browse(option_value_openerp_id)
            yield option_value_object

    @mapping
    def name(self, record):
        # revisar el estado de las caracteristicas
        template = self.main_template(record)
        options = []
        for option_value_object in self._get_option_value(record):
            key = option_value_object.attribute_id.name
            value = option_value_object.name
            options.append('%s:%s' % (key, value))
        return {'name_template': template.name}

    @mapping
    def attribute_value_ids(self, record):
        results = []
        for option_value_object in self._get_option_value(record):
            results.append(option_value_object.openerp_id.id)
        return {'attribute_value_ids': [(6, 0, results)]}

    @mapping
    def main_template_id(self, record):    
        return {'main_template_id': self.get_main_template_id(record)}

    def _template_code_exists(self, code):
        model = self.session.pool.get('product.product')
        combination_binder = self.binder_for('prestashop.product.combination')
        template_ids = self.env['product.product'].search([
            ('default_code', '=', code),
            ('company_id', '=', self.backend_record.company_id.id),
        ])
        return template_ids and not combination_binder.to_backend(template_ids,unwrap=True, wrap=True)

    @mapping
    def default_code(self, record):        
        code = record.get('reference')
        if not code:
            code = "%s_%s" % (record['id_product'], record['id'])
        if not self._template_code_exists(code):
            return {'default_code': code}
        i = 1
        current_code = '%s_%s' % (code, i)
        while self._template_code_exists(current_code):
            i += 1
            current_code = '%s_%s' % (code, i)
        return {'default_code': current_code}

    @mapping
    def backend_id(self, record):
        return {'backend_id': self.backend_record.id}

    # @mapping
    # def length(self, record):          
    #     backend_adapter = self.unit_for(GenericAdapter, 'prestashop.product.template')
    #     main_template = backend_adapter.read(record['id_product'])
    #     return {'length': main_template['depth']}
    
    # @mapping
    # def height (self, record):
    #     backend_adapter = self.unit_for(GenericAdapter, 'prestashop.product.template')
    #     main_template = backend_adapter.read(record['id_product'])
    #     return {'height': main_template['height']}
    
    # @mapping
    # def width(self, record):  
    #     backend_adapter = self.unit_for(GenericAdapter, 'prestashop.product.template')
    #     main_template = backend_adapter.read(record['id_product'])
    #     return {'width': main_template['width']}