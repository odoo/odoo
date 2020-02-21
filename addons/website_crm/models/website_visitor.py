# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models, api


class WebsiteVisitor(models.Model):
    _inherit = 'website.visitor'

    lead_ids = fields.Many2many('crm.lead', string='Leads', groups="sales_team.group_sale_salesman")
    lead_count = fields.Integer('# Leads', compute="_compute_lead_count", groups="sales_team.group_sale_salesman")

    @api.depends('lead_ids')
    def _compute_lead_count(self):
        for visitor in self:
            visitor.lead_count = len(visitor.lead_ids)

    @api.depends('partner_id.email_normalized', 'partner_id.mobile', 'lead_ids.email_normalized', 'lead_ids.mobile')
    def _compute_email_phone(self):
        super(WebsiteVisitor, self)._compute_email_phone()
        self.flush()

        left_visitors = self.filtered(lambda visitor: not visitor.email or not visitor.mobile)
        leads = left_visitors.mapped('lead_ids').sorted('create_date', reverse=True)
        visitor_to_lead_ids = dict((visitor.id, visitor.lead_ids.ids) for visitor in left_visitors)

        for visitor in left_visitors:
            visitor_leads = leads.filtered(lambda lead: lead.id in visitor_to_lead_ids[visitor.id])
            if not visitor.email:
                visitor.email = next((lead.email_normalized for lead in visitor_leads if lead.email_normalized), False)
            if not visitor.mobile:
                visitor.mobile = next((lead.mobile or lead.phone for lead in visitor_leads if lead.mobile or lead.phone), False)

    def _prepare_visitor_send_mail_values(self):
        visitor_mail_values = super(WebsiteVisitor, self)._prepare_visitor_send_mail_values()
        if self.lead_ids:
            lead = self.lead_ids._sort_by_confidence_level(reverse=True)[0]
            partner_id = self.partner_id.id
            if not self.partner_id:
                partner_id = lead.handle_partner_assignation()[lead.id]
                if not lead.partner_id:
                    lead.partner_id = partner_id
                self.partner_id = partner_id
            return {
                'res_model': 'crm.lead',
                'res_id': lead.id,
                'partner_ids': [partner_id],
            }
        return visitor_mail_values
