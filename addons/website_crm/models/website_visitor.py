# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models, api


class WebsiteVisitor(models.Model):
    _inherit = 'website.visitor'

    lead_ids = fields.One2many('crm.lead', 'visitor_id', string='Leads')
    lead_count = fields.Integer('# Leads', compute="_compute_lead_count")

    @api.depends('lead_ids.visitor_id')
    def _compute_lead_count(self):
        page_data = self.env['crm.lead'].read_group([('visitor_id', 'in', self.ids)], ['visitor_id'], ['visitor_id'])
        mapped_data = dict([(data['visitor_id'][0], data['visitor_id_count']) for data in page_data])
        for visitor in self:
            visitor.lead_count = mapped_data.get(visitor.id, 0)
