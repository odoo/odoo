# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class ResPartner(models.Model):
    _inherit = 'res.partner'

    claim_count = fields.Integer(compute='_compute_claim_count')

    def _compute_claim_count(self):
        partner_data = self.env['crm.claim'].read_group([('partner_id', 'in', self.ids)], [], groupby="partner_id")
        result = dict((data['partner_id'][0], data['partner_id_count']) for data in partner_data)
        for partner in self:
            partner.claim_count = result.get(partner.id, 0)
