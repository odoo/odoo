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

    def _check_for_message_composer(self):
        check = super(WebsiteVisitor, self)._check_for_message_composer()
        if not check and self.lead_ids:
            sorted_leads = self.lead_ids._sort_by_confidence_level(reverse=True)
            partners = sorted_leads.mapped('partner_id')
            if not partners:
                main_lead = self.lead_ids[0]
                partner_id = main_lead.handle_partner_assignation(action='create')[main_lead.id]
                if not main_lead.partner_id:
                    main_lead.partner_id = partner_id
                self.partner_id = partner_id
            return True
        return check

    def _prepare_message_composer_context(self):
        if not self.partner_id and self.lead_ids:
            sorted_leads = self.lead_ids._sort_by_confidence_level(reverse=True)
            lead_partners = sorted_leads.mapped('partner_id')
            partner = lead_partners[0] if lead_partners else False
            if partner:
                return {
                    'default_model': 'crm.lead',
                    'default_res_id': sorted_leads[0].id,
                    'default_partner_ids': partner.ids,
                }
        return super(WebsiteVisitor, self)._prepare_message_composer_context()
