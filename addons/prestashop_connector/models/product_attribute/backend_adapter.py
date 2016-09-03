from ...backend import prestashop
from ...unit.backend_adapter import GenericAdapter

@prestashop
class ProductAttributeAdapter(GenericAdapter):
    _model_name = 'prestashop.product.attribute'
    _prestashop_model = 'product_options'

@prestashop
class ProductAttributeValueAdapter(GenericAdapter):
    _model_name = 'prestashop.product.attribute.value'
    _prestashop_model = 'product_option_values'