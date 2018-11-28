# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import models, api


class Partner(models.Model):
    _inherit = 'res.partner'

    @api.model
    def name_search_icon(self, name, args=None, operator='ilike', limit=100):
        result = []
        type_icons = {
            'delivery': "fa fa-truck",
            'invoice': "fa fa-money"
        }
        res = super(Partner, self).name_search_icon(name, args, operator=operator, limit=limit)
        records = self.browse([r[0] for r in res])
        icon_map = dict([(r.id, type_icons.get(r.type, '')) for r in records])
        for r in res:
            result.append((r[0], r[1], icon_map[r[0]]))
        return result
