# Part of Odoo. See LICENSE file for full copyright and licensing details.

from . import models
from odoo.tools import column_exists, create_column


def pre_init_hook(env):
    """Do not compute the l10n_dk_currency_rate_at_transaction field on existing Moves."""
    if not column_exists(env.cr, "account_move", "l10n_dk_currency_rate_at_transaction"):
        create_column(env.cr, "account_move", "l10n_dk_currency_rate_at_transaction", "numeric")
