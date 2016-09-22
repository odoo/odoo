# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class ResPartner(models.Model):
    _inherit = 'res.partner'

    issue_count = fields.Integer(compute='_compute_issue_count', string='# Issues')

    def _compute_issue_count(self):
        Issue = self.env['project.issue']
        for partner in self:
            partner.issue_count = Issue.search_count([('partner_id', 'child_of', partner.commercial_partner_id.id)])
