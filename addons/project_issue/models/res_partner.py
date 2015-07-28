# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class ResPartner(models.Model):
    _inherit = 'res.partner'

    issue_count = fields.Integer(compute='_compute_issue_count', string='# Issues')

    def _compute_issue_count(self):
        Issue = self.pool['project.issue']
        partners = {id: self.search([('id', 'child_of', self.ids)]) for id in self.ids}
        for partner_id in partners.keys():
            partner.issue_count = Issue.search_count([('partner_id', 'in', partners[partner_id])])
