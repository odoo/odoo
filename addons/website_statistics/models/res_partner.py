# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
import json

from psycopg2 import IntegrityError

from odoo import api, fields, models, tools
from odoo.osv import expression
from odoo.http import request


class ResPartner(models.Model):
    _inherit = 'res.partner'

    statistics_ids = fields.One2many('statistics.statistics', 'partner_id', string="Tracked activities")

    def get_statistics_last_viewed(self, res_model, excluded_ids=[], quantity=12):
        domain = expression.AND([[('partner_id', '=', self.id)], [('res_model', '=', res_model)]])
        if excluded_ids:
            domain = expression.AND([domain, [('res_id', 'not in', excluded_ids)]])
        record_ids = self.env['statistics.statistics'].search(domain, limit=quantity, order='view_date desc, id desc').mapped('res_id')
        return self.env[res_model].browse(record_ids)

    def add_statistics_view(self, res_model, res_id):
        res_model_id = self.env['ir.model'].search([('model', '=', res_model)], limit=1).id
        return self.env['statistics.statistics'].update_statistics_view({
            'res_model_id': res_model_id,
            'res_id': res_id,
            'partner_id': self.id,
        })
