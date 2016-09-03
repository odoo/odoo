import logging

from ...backend import prestashop
from ...unit.import_synchronizer import PrestashopImportSynchronizer
from openerp.addons.connector.unit.backend_adapter import BackendAdapter

_logger = logging.getLogger(__name__)

@prestashop
class ProductCombinationRecordImport(PrestashopImportSynchronizer):
    _model_name = 'prestashop.product.combination'
      
    def _import_dependencies(self):
        record = self.prestashop_record
        option_values = record.get('associations', {}).get(
            'product_option_values', {}).get('product_option_values', [])
        if not isinstance(option_values, list):
            option_values = [option_values]
        backend_adapter = self.unit_for(
            BackendAdapter,
            'prestashop.product.attribute.value'
        )
        for option_value in option_values:
            option_value = backend_adapter.read(option_value['id'])
            self._import_dependency(
                option_value['id'],
                'prestashop.product.attribute.value'
            )

    def unit_price_impact(self, erp_id):
        record = self.prestashop_record
        _logger.debug("Record pour extra price")
        _logger.debug(record)
        _logger.debug(erp_id)
        unit_price_impact = float(record['unit_price_impact']) or 0.0
        _logger.debug("Unit price impact : %s ", 
                                            str(unit_price_impact))
                                            
        main_template = erp_id.product_tmpl_id
        _logger.debug("Template : %s ")
        _logger.debug(main_template)
        
        option_values = record.get('associations', {}).get(
            'product_option_values', {}).get('product_option_value', [])
        _logger.debug(option_values)
        
        for option_value_object in option_values:
            _logger.debug(option_value_object)

