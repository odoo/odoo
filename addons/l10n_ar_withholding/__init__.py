# Part of Odoo. See LICENSE file for full copyright and licensing details.

from . import models
from . import wizards
from . import demo


def _l10n_ar_wth_post_init(env):
    """ Existing companies that have the Argentinean Chart of Accounts set """
    env['account.chart.template']._l10n_ar_wth_post_init()
