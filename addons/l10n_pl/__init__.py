# Part of Odoo. See LICENSE file for full copyright and licensing details.
from . import models

from .models.account_move import AccountMove
from .models.l10n_pl_tax_office import L10n_PlL10n_Pl_Tax_Office
from .models.product import ProductTemplate
from .models.res_company import ResCompany
from .models.res_config_settings import ResConfigSettings
from .models.res_partner import ResPartner
from .models.template_pl import AccountChartTemplate

def _preserve_tag_on_taxes(env):
    from odoo.addons.account.models.chart_template import preserve_existing_tags_on_taxes
    preserve_existing_tags_on_taxes(env, 'l10n_pl')

def post_init_hook(env):
    _preserve_tag_on_taxes(env)
