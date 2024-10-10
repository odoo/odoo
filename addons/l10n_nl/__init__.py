# Part of Odoo. See LICENSE file for full copyright and licensing details.

# Copyright (C) 2016 Onestein (<http://www.onestein.eu>).

from odoo.addons.account.models.chart_template import set_non_trade_accounts

from . import models


def _post_init_hook(cr, registry):
    set_non_trade_accounts(cr, 'l10n_nl', 'l10n_nl.l10nnl_chart_template', ('1590',))
