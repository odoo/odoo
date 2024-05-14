# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.addons.account.models.chart_template import set_non_trade_accounts

from . import demo
from . import models


def _post_init_hook(cr, registry):
    set_non_trade_accounts(cr, 'l10n_cl', 'l10n_cl.cl_chart_template', ('account_110760', 'account_210711'))
