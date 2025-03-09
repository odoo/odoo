# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.addons.account.models.chart_template import set_non_trade_accounts


def _post_init_hook(cr, registry):
    set_non_trade_accounts(
        cr, 'l10n_de_skr03', 'l10n_de_skr03.l10n_de_chart_template', ('account_1545', 'account_1797')
    )
