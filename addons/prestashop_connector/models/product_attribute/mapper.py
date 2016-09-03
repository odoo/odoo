from ...backend import prestashop
from ...unit.mapper import PrestashopImportMapper, mapping

@prestashop
class ProductAttributeMapper(PrestashopImportMapper):
    _model_name = 'prestashop.product.attribute'

    @mapping
    def name(self, record):
        return {'name':record['name']['language']['value']}
    
    @mapping
    def backend_id(self, record):
        return {'backend_id': self.backend_record.id}

@prestashop
class ProductAttributeValueMapper(PrestashopImportMapper):
    _model_name = 'prestashop.product.attribute.value'
    
    direct = [
        ('position', 'sequence'),
    ]
    
    @mapping
    def name(self, record):
        return {'name':record['name']['language']['value']}
    
    @mapping
    def backend_id(self, record):
        return {'backend_id': self.backend_record.id}

    @mapping
    def attribute_id(self, record):
        attribute_id = self.get_openerp_id(
            'prestashop.product.attribute',
            record['id_attribute_group']
        )
        
        return {'attribute_id': attribute_id}