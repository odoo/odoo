# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, SUPERUSER_ID


class Lead(models.Model):
    _inherit = 'crm.lead'

    visitor_ids = fields.Many2many('website.visitor', string="Web Visitors")
    visitor_page_count = fields.Integer('# Page Views', compute="_compute_visitor_page_count")

    @api.depends('visitor_ids.page_ids')
    def _compute_visitor_page_count(self):
        mapped_data = {}
        if self.ids:
            self.flush(['visitor_ids'])
            sql = """ SELECT l.id as lead_id, count(*) as page_view_count
                        FROM crm_lead l
                        JOIN crm_lead_website_visitor_rel lv ON l.id = lv.crm_lead_id
                        JOIN website_visitor v ON v.id = lv.website_visitor_id
                        JOIN website_track p ON p.visitor_id = v.id
                        WHERE l.id in %s AND v.active = TRUE
                        GROUP BY l.id"""
            self.env.cr.execute(sql, (tuple(self.ids),))
            page_data = self.env.cr.dictfetchall()
            mapped_data = {data['lead_id']: data['page_view_count'] for data in page_data}
        for lead in self:
            lead.visitor_page_count = mapped_data.get(lead.id, 0)

    def action_redirect_to_page_views(self):
        visitors = self.visitor_ids
        action = self.env["ir.actions.actions"]._for_xml_id("website.website_visitor_page_action")
        action['domain'] = [('visitor_id', 'in', visitors.ids)]
        # avoid grouping if only few records
        if len(visitors.website_track_ids) > 15 and len(visitors.website_track_ids.page_id) > 1:
            action['context'] = {'search_default_group_by_page': '1'}
        return action

    def _merge_get_fields_specific(self):
        fields_info = super(Lead, self)._merge_get_fields_specific()
        # add all the visitors from all lead to merge
        fields_info['visitor_ids'] = lambda fname, leads: [(6, 0, leads.visitor_ids.ids)]
        return fields_info

    def website_form_input_filter(self, request, values):
        values['medium_id'] = values.get('medium_id') or \
                              self.default_get(['medium_id']).get('medium_id') or \
                              self.sudo().env.ref('utm.utm_medium_website').id
        values['team_id'] = values.get('team_id') or \
                            request.website.crm_default_team_id.id
        values['user_id'] = values.get('user_id') or \
                            request.website.crm_default_user_id.id
        values['type'] = 'lead' if self.with_user(SUPERUSER_ID).env['res.users'].has_group('crm.group_use_lead') else 'opportunity'
        return values
