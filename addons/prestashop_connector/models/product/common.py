import logging
from ...backend import prestashop
from ...unit.import_synchronizer import TranslatableRecordImport,import_record

_logger = logging.getLogger(__name__)

@prestashop
class TemplateRecordImport(TranslatableRecordImport):

    """ Import one translatable record """
    _model_name = [
        'prestashop.product.template',
    ]

    _translatable_fields = {
        'prestashop.product.template': [
            'meta_title',
            'meta_description',
            'link_rewrite',
            'description',
            'name',
            'description_short',
        ],
    }

    def _import_dependencies(self):
        self._import_product_brand()

    def _import_product_brand(self):
        record = self.prestashop_record
        
        manufacturer_name = record['manufacturer_name']['value']
        if not manufacturer_name:
            return
        
        brand = self.env['product.brand'].search([('name','=',manufacturer_name.strip())])

        if not brand:
            brand_set = {
                'name': manufacturer_name.strip(),
            }
            brand = self.env['product.brand'].with_context(self.session.context).create(brand_set)
            
        self.prestashop_record['product_brand_id'] = brand.id

    def _after_import(self, erp_id):
        self.import_combinations()
        self.attribute_line(erp_id.id)
        self.deactivate_default_product(erp_id.id)

    def deactivate_default_product(self, erp_id):
        template = self.env['prestashop.product.template'].browse(erp_id)
                
        if template.product_variant_count != 1:
            for product in template.product_variant_ids:                
                if not product.attribute_value_ids:
                    # self.session.write('product.product', [product.id],
                    #                    {'active': False})
                    product.write({'active': False})

    def attribute_line(self, erp_id):
        _logger.debug("GET ATTRIBUTES LINE")
        
        template = self.env['prestashop.product.template'].browse(erp_id)
        attr_line_value_ids = []
        
        for attr_line in template.attribute_line_ids:
            attr_line_value_ids.extend(attr_line.value_ids.ids)
        
        template_id = template.openerp_id.id
        products = self.env['product.product'].search([('product_tmpl_id', '=', template_id)])
        
        if products:
            attribute_ids = []

            for product in products:
                for attribute_value in product.attribute_line_ids:
                    attribute_ids.append(attribute_value.attribute_id.id)

            _logger.debug("Attributes to ADD")
            _logger.debug(attribute_ids)
            
            if attribute_ids:
                for attribute_id in set(attribute_ids):
                    value_ids = []
                    for product in products:                        
                        for attribute_value in product.attribute_value_ids:                                                      
                            if (attribute_value.attribute_id.id == attribute_id
                                and attribute_value.id not in attr_line_value_ids):
                                value_ids.append(attribute_value.id)
                    
                    if value_ids:
                        attr_line_model = self.session.pool.get('product.attribute.line')
                        attr_line_model.with_context(self.session.context).create({
                            'attribute_id': attribute_id,
                            'product_tmpl_id': template_id,
                            'value_ids': [(6, 0, set(value_ids))]
                            }
                        )

    def import_combinations(self):
        prestashop_record = self._get_prestashop_data()
        associations = prestashop_record.get('associations', {})

        combinations = associations.get('combinations', {}).get(
            'combinations', [])
        if not isinstance(combinations, list):
            combinations = [combinations]
        
        priority = 15
        for combination in combinations:            
            import_record(
                self.session,
                'prestashop.product.combination',
                self.backend_record.id,
                combination['id'],                                       
            )