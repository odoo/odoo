# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import SUPERUSER_ID, api
from odoo.addons.account.models.chart_template import set_non_trade_accounts


def _post_init_hook(cr, registry):
    env = api.Environment(cr, SUPERUSER_ID, {})
    env.ref('l10n_bo.bo_chart_template').process_coa_translations()

    set_non_trade_accounts(cr, 'l10n_bo', 'l10n_bo.bo_chart_template', ('l10n_bo_1141', 'l10n_bo_1142'))
