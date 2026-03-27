# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import re

from odoo import api, fields, models


class CrmPaymentMethod(models.Model):
    _name = 'crm.payment.method'
    _description = 'CRM Payment Method'
    _order = 'sequence, name'

    name = fields.Char(string='Nombre', required=True, translate=True)
    code = fields.Char(string='Codigo', required=True)
    sequence = fields.Integer(string='Secuencia', default=10)
    active = fields.Boolean(string='Activo', default=True)

    _sql_constraints = [
        ('crm_payment_method_code_unique', 'unique(code)', 'El codigo debe ser unico.'),
    ]

    @staticmethod
    def _build_code_from_name(name):
        code = re.sub(r'[^a-z0-9]+', '_', (name or '').strip().lower()).strip('_')
        return code or 'forma_pago'

    @classmethod
    def _next_unique_code(cls, env, base_code):
        code = base_code
        index = 1
        while env['crm.payment.method'].search_count([('code', '=', code)]):
            index += 1
            code = f"{base_code}_{index}"
        return code

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if not vals.get('code') and vals.get('name'):
                base_code = self._build_code_from_name(vals['name'])
                vals['code'] = self._next_unique_code(self.env, base_code)
        return super().create(vals_list)
