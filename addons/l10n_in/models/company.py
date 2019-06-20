# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models


class ResCompany(models.Model):
    _inherit = "res.company"

    l10n_in_unit_ids = fields.One2many('res.partner', 'company_l10n_in_unit_id', string="Operating Units")

    @api.model
    def create(self, vals):
        # company's partner will now act as it's unit
        partner = self.env['res.partner']
        if vals.get('partner_id'):
            partner = partner.browse(vals['partner_id'])
        company = super(ResCompany, self).create(vals)
        (partner or company.partner_id).company_l10n_in_unit_id = company
        return company
