# Part of Odoo. See LICENSE file for full copyright and licensing details.

from . import models
from . import wizard


def _auto_install_sale_app(env):
    """Make sure you have at least one "Sales" app to use the advanced delivery logic.

    Either you have e-commerce (website_sale) or Sales (sale_management)
    """
    if env['ir.module.module']._get('website_sale').state != 'uninstalled':
        return
    module_sale_management = env['ir.module.module']._get('sale_management')
    if module_sale_management.state == 'uninstalled':
        module_sale_management.button_install()
