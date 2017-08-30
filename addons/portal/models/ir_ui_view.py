# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, models


class View(models.Model):
    _inherit = 'ir.ui.view'

    @api.model
    def postprocess_and_fields(self, model, node, view_id):
        if node.tag == 'form' and not node.get('share') and isinstance(self.env[model], type(self.env['portal.mixin'])):
            node.set('share', 'true')
        return super(View, self).postprocess_and_fields(model=model, node=node, view_id=view_id)
