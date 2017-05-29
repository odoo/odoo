# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import models
from openerp import api, SUPERUSER_ID
# FORWARD PORT NOTICE
# In master as of March 2017, RCO-ODOO coded an exclusive field on modules to flag incompatibility
def _check_incompatibility(cr, registry):
    env = api.Environment(cr, SUPERUSER_ID, {})
    wanted_states = ['installed', 'to upgrade', 'to install']
    Module = env['ir.module.module']
    l10n_fr_certification = Module.search([('name', '=', 'l10n_fr_certification')])

    if l10n_fr_certification and l10n_fr_certification.state in wanted_states:
        from openerp.addons.l10n_fr_certification import _setup_inalterability
        _setup_inalterability(cr, registry)
