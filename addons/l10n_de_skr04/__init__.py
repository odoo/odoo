# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.addons.account.models.chart_template import set_non_trade_accounts


def _post_init_hook(cr, registry):
    set_non_trade_accounts(
        cr, 'l10n_de_skr04', 'l10n_de_skr04.l10n_chart_de_skr04', ('chart_skr04_1421', 'chart_skr04_3860')
    )
