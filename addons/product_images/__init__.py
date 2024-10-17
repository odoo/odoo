# Part of Odoo. See LICENSE file for full copyright and licensing details.

from . import models
from . import wizard

from .models.ir_cron_trigger import IrCronTrigger
from .models.product import ProductProduct
from .models.res_config_settings import ResConfigSettings
from .wizard.product_fetch_image_wizard import ProductFetchImageWizard


def uninstall_hook(env):
    ICP = env['ir.config_parameter']
    ICP.set_param('google.pse.id', False)
    ICP.set_param('google.custom_search.key', False)
