# Part of Odoo. See LICENSE file for full copyright and licensing details.
from . import models

def _preserve_tag_on_taxes(env):
    from odoo.addons.account.models.chart_template import preserve_existing_tags_on_taxes
from .models.account_move import AccountMove
from .models.ir_actions_report import IrActionsReport
from .models.res_bank import ResPartnerBank
from .models.res_partner import ResPartner
from .models.template_th import AccountChartTemplate
    preserve_existing_tags_on_taxes(env, 'l10n_th')
