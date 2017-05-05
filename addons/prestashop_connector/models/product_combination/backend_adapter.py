from ...backend import prestashop
from ...unit.backend_adapter import GenericAdapter

@prestashop
class ProductCombinationAdapter(GenericAdapter):
    _model_name = 'prestashop.product.combination'
    _prestashop_model = 'combinations'