# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import models
from odoo import api, SUPERUSER_ID


def _check_incompatibility(cr, registry):
    env = api.Environment(cr, SUPERUSER_ID, {})
    wanted_states = ['installed', 'to upgrade', 'to install']

    l10n_fr_certification = env['ir.module.module'].search([('name', '=', 'l10n_fr_certification')])
    if l10n_fr_certification and l10n_fr_certification.state in wanted_states:
        from odoo.addons.l10n_fr_certification import _deactivate_account_cancel_views
        _deactivate_account_cancel_views(cr, registry)
