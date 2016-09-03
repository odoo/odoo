from ...backend import prestashop
from ...unit.backend_adapter import GenericAdapter

@prestashop
class ProductTemplateAdapter(GenericAdapter):
    _model_name = 'prestashop.product.template'
    _prestashop_model = 'products'
    _export_node_name = 'product'