# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.


from odoo import models, fields, api
from odoo.osv import expression


class EtaActivityType(models.Model):
    _name = 'l10n_eg_edi.activity.type'
    _description = 'ETA code for activity type'

    name = fields.Char(required=True, translate=True)
    code = fields.Char(required=True)

    @api.model
    def _name_search_domain(self, name='', args=None, operator='ilike'):
        args = args or []
        if operator == 'ilike' and not(name or '').strip():
            domain = []
        else:
            domain = ['|', ('name', operator, name), ('code', operator, name)]
        return expression.AND([domain, args])
