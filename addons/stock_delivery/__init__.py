# Part of Odoo. See LICENSE file for full copyright and licensing details.

from . import models
from . import wizard

from .models.delivery_carrier import DeliveryCarrier
from .models.product_template import ProductTemplate
from .models.sale_order import SaleOrder, SaleOrderLine
from .models.stock_move import StockMove, StockMoveLine, StockRoute
from .models.stock_package_type import StockPackageType
from .models.stock_picking import StockPicking
from .models.stock_quant_package import StockQuantPackage
from .wizard.choose_delivery_carrier import ChooseDeliveryCarrier
from .wizard.choose_delivery_package import ChooseDeliveryPackage
from .wizard.stock_return_picking import StockReturnPicking


def _auto_install_sale_app(env):
    """Make sure you have at least one "Sales" app to use the advanced delivery logic.

    Either you have e-commerce (website_sale) or Sales (sale_management)
    """
    if env['ir.module.module']._get('website_sale').state != 'uninstalled':
        return
    module_sale_management = env['ir.module.module']._get('sale_management')
    if module_sale_management.state == 'uninstalled':
        module_sale_management.button_install()
