# -*- coding: utf-8 -*-

import odoo

def migrate(cr, version):
    registry = odoo.registry(cr.dbname)
    from odoo.addons.account.models.chart_template import migrate_set_tags_and_taxes_updatable
    migrate_set_tags_and_taxes_updatable(cr, registry, 'l10n_nl')
