# -*- coding: ascii -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, models
from odoo.addons.http_routing.models.ir_http import slug, unslug_url


class IrUiView(models.Model):
    _inherit = ["ir.ui.view"]

    @api.model
    def _prepare_qcontext(self):
        qcontext = super(IrUiView, self)._prepare_qcontext()
        qcontext['slug'] = slug
        qcontext['unslug_url'] = unslug_url
        return qcontext


class BaseModel(models.AbstractModel):
    _inherit = 'base'

    def _slug_format(self):
        # read from a config
        return "{name}"

    def _slug_values(self):
        return {
            'id': self.id,
            'display_name': self.display_name or '',
            'name': self.name or '',
        }
