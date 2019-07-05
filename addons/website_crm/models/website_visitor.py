# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models, api


class WebsiteVisitor(models.Model):
    _inherit = 'website.visitor'

    lead_ids = fields.One2many('crm.lead', 'visitor_id', string='Leads')
    lead_count = fields.Integer('# Leads', compute="_compute_lead_count")
    type = fields.Selection(selection_add=[('lead', 'Lead')])

    @api.depends('lead_ids')
    def _compute_lead_count(self):
        for visitor in self:
            visitor.lead_count = len(visitor.lead_ids)

    @api.depends('partner_ids', 'lead_ids')
    def _compute_type(self):
        for visitor in self:
            if visitor.partner_ids:
                visitor.type = 'customer'
            elif visitor.lead_ids:
                visitor.type = 'lead'
            else:
                visitor.type = 'visitor'
