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
        sql = """ SELECT v.id as visitor_id, l.id as lead_id,
                  CASE WHEN p.email_normalized is not null THEN p.email_normalized ELSE l.email_normalized END as email,
                  CASE WHEN p.mobile is not null THEN p.mobile WHEN l.mobile is not null THEN l.mobile ELSE l.phone END as mobile
                  FROM website_visitor v
                  JOIN crm_lead_website_visitor_rel lv on lv.website_visitor_id = v.id
                  JOIN crm_lead l ON lv.crm_lead_id = l.id
                  LEFT JOIN res_partner p on p.id = v.partner_id
                  WHERE v.id in %s
                  ORDER BY l.create_date ASC"""
        self.env.cr.execute(sql, (tuple(self.ids),))
        results = self.env.cr.dictfetchall()
        mapped_data = {}
        for result in results:
            visitor_info = mapped_data.get(result['visitor_id'], {'email': '', 'mobile': ''})
            if result['email']:
                visitor_info['email'] = result['email']
            if result['mobile']:
                visitor_info['mobile'] = result['mobile']
            mapped_data[result['visitor_id']] = visitor_info

        for visitor in self:
            email = mapped_data.get(visitor.id, {}).get('email')
            visitor.email = email[:-1] if email else False
            visitor.mobile = mapped_data.get(visitor.id, {}).get('mobile')

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
