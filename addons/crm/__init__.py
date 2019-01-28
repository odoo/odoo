# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from functools import partial
import odoo
from odoo import api, SUPERUSER_ID

import controllers
import models
import report
import wizard


def uninstall_hook(cr, registry):
    def update_dashboard_graph_model(dbname):
        db_registry = odoo.modules.registry.RegistryManager.new(dbname)
        with api.Environment.manage(), db_registry.cursor() as cr:
            env = api.Environment(cr, SUPERUSER_ID, {})
            if 'crm.team' in env:
                vals = [v[0] for v in env['crm.team']._fields['dashboard_graph_model'].selection]
                recs = env['crm.team'].search([('dashboard_graph_model', 'not in', vals)])
                recs.write({'dashboard_graph_model': None})
    cr.after("commit", partial(update_dashboard_graph_model, cr.dbname))
