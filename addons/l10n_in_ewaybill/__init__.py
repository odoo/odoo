# Part of Odoo. See LICENSE file for full copyright and licensing details.

from . import models
from . import demo
from . import wizard


def _l10n_in_ewb_post_init(env):
    if env.ref('base.module_l10n_in_ewaybill').demo:
        env['account.chart.template']._update_l10n_in_demo_data()
