# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models


class ResCompany(models.Model):
    _inherit = 'res.company'

    manufacturing_lead = fields.Float(
        'Manufacturing Lead Time', default=0.0, required=True,
        help="Security days for each manufacturing operation.")

    def _create_unbuild_sequence(self):
        unbuild_vals = []
        for company in self:
            unbuild_vals.append({
                'name': 'Unbuild',
                'code': 'mrp.unbuild',
                'company_id': company.id,
                'prefix': 'UB/',
                'padding': 5,
                'number_next': 1,
                'number_increment': 1
            })
        if unbuild_vals:
            self.env['ir.sequence'].create(unbuild_vals)

    @api.model
    def create_missing_unbuild_sequences(self):
        company_ids  = self.env['res.company'].search([])
        company_has_unbuild_seq = self.env['ir.sequence'].search([('code', '=', 'mrp.unbuild')]).company_id
        company_todo_sequence = company_ids - company_has_unbuild_seq
        company_todo_sequence._create_unbuild_sequence()

    def _create_per_company_sequences(self):
        super()._create_per_company_sequences()
        self._create_unbuild_sequence()
