# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from openerp import api, fields, models


class ResPartner(models.Model):
    """ Inherits partner and adds Issue information in the partner form """
    _inherit = 'res.partner'

    issue_count = fields.Integer(compute='_issue_count', string='# Issues')

    @api.multi
    def _issue_count(self):
        ProjectIssue = self.env['project.issue']
        for partner in self:
            partner.issue_count = ProjectIssue.search_count([('partner_id', '=', partner.id)])
