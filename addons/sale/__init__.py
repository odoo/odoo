# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from . import models
from . import controllers
from . import report
from . import wizard

from functools import partial
import odoo
from odoo import api, SUPERUSER_ID



def uninstall_hook(cr, registry):
    def update_dashboard_graph_model(dbname):
        db_registry = odoo.modules.registry.Registry.new(dbname)
        with api.Environment.manage(), db_registry.cursor() as cr:
            env = api.Environment(cr, SUPERUSER_ID, {})
            if 'crm.team' in env:
                recs = env['crm.team'].search([])
                for rec in recs:
                    rec._onchange_team_type()

    cr.after("commit", partial(update_dashboard_graph_model, cr.dbname))
