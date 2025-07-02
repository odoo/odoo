# -*- encoding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from . import models
from . import wizard


def _l10n_sa_post_init(env):
    env['res.lang'].search([('code', 'in', ['ar_001', 'en_US'])]).write({
        'date_format': "%Y-%m-%d"
    })
