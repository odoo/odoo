# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from operator import itemgetter
from odoo import api, models

class IrUiView(models.Model):
    _inherit = 'ir.ui.view'

    @api.model
    def _validate_custom_views(self, model):
        # views from imported modules should be considered as custom views
        result = super(IrUiView, self)._validate_custom_views(model)

        self._cr.execute("""
            SELECT max(v.id)
               FROM ir_ui_view v
          LEFT JOIN ir_model_data md ON (md.model = 'ir.ui.view' AND md.res_id = v.id)
          LEFT JOIN ir_module_module m ON (m.name = md.module)
              WHERE m.imported = true
                AND v.model = %s
                AND v.active = true
           GROUP BY coalesce(v.inherit_id, v.id)
        """, [model])

        ids = map(itemgetter(0), self._cr.fetchall())
        views = self.with_context(load_all_views=True).browse(ids)
        return views._check_xml() and result
