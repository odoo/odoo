# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import random

from odoo.addons.base_geolocalize.models.res_partner import geo_find, geo_query_address
from odoo import api, fields, models, _
from odoo.tools import pycompat


class CrmLead(models.Model):
    _inherit = "crm.lead"
    partner_latitude = fields.Float('Geo Latitude', digits=(16, 5))
    partner_longitude = fields.Float('Geo Longitude', digits=(16, 5))
    partner_assigned_id = fields.Many2one('res.partner', 'Assigned Partner', track_visibility='onchange', help="Partner this case has been forwarded/assigned to.", index=True)
    partner_declined_ids = fields.Many2many(
        'res.partner',
        'crm_lead_declined_partner',
        'lead_id',
        'partner_id',
        string='Partner not interested')
    date_assign = fields.Date('Assignation Date', help="Last date this case was forwarded/assigned to a partner")

    @api.multi
    def _merge_data(self, fields):
        fields += ['partner_latitude', 'partner_longitude', 'partner_assigned_id', 'date_assign']
        return super(CrmLead, self)._merge_data(fields)

    @api.onchange("partner_assigned_id")
    def onchange_assign_id(self):
        """This function updates the "assignation date" automatically, when manually assign a partner in the geo assign tab
        """
        partner_assigned = self.partner_assigned_id
        if not partner_assigned:
            self.date_assign = False
        else:
            self.date_assign = fields.Date.context_today(self)
            self.user_id = partner_assigned.user_id

    @api.multi
    def assign_salesman_of_assigned_partner(self):
        salesmans_leads = {}
        for lead in self:
            if (lead.stage_id.probability > 0 and lead.stage_id.probability < 100) or lead.stage_id.sequence == 1:
                if lead.partner_assigned_id and lead.partner_assigned_id.user_id != lead.user_id:
                    salesmans_leads.setdefault(lead.partner_assigned_id.user_id.id, []).append(lead.id)

        for salesman_id, leads_ids in pycompat.items(salesmans_leads):
            leads = self.browse(leads_ids)
            leads.write({'user_id': salesman_id})
            for lead in leads:
                lead._onchange_user_id()

    @api.multi
    def action_assign_partner(self):
        return self.assign_partner(partner_id=False)

    @api.multi
    def assign_partner(self, partner_id=False):
        partner_dict = {}
        res = False
        if not partner_id:
            partner_dict = self.search_geo_partner()
        for lead in self:
            if not partner_id:
                partner_id = partner_dict.get(lead.id, False)
            if not partner_id:
                tag_to_add = self.env.ref('website_crm_partner_assign.tag_portal_lead_partner_unavailable', False)
                lead.write({'tag_ids': [(4, tag_to_add.id, False)]})
                continue
            lead.assign_geo_localize(lead.partner_latitude, lead.partner_longitude,)
            partner = self.env['res.partner'].browse(partner_id)
            if partner.user_id:
                lead.allocate_salesman(partner.user_id.ids, team_id=partner.team_id.id)
            values = {'date_assign': fields.Date.context_today(lead), 'partner_assigned_id': partner_id}
            lead.write(values)
        return res

    @api.multi
    def assign_geo_localize(self, latitude=False, longitude=False):
        if latitude and longitude:
            self.write({
                'partner_latitude': latitude,
                'partner_longitude': longitude
            })
            return True
        # Don't pass context to browse()! We need country name in english below
        for lead in self:
            if lead.partner_latitude and lead.partner_longitude:
                continue
            if lead.country_id:
                result = geo_find(geo_query_address(street=lead.street,
                                                    zip=lead.zip,
                                                    city=lead.city,
                                                    state=lead.state_id.name,
                                                    country=lead.country_id.name))

                if result is None:
                    result = geo_find(geo_query_address(
                        city=lead.city,
                        state=lead.state_id.name,
                        country=lead.country_id.name
                    ))

                if result:
                    lead.write({
                        'partner_latitude': result[0],
                        'partner_longitude': result[1]
                    })
        return True

    @api.multi
    def search_geo_partner(self):
        Partner = self.env['res.partner']
        res_partner_ids = {}
        self.assign_geo_localize()
        for lead in self:
            partner_ids = []
            if not lead.country_id:
                continue
            latitude = lead.partner_latitude
            longitude = lead.partner_longitude
            if latitude and longitude:
                # 1. first way: in the same country, small area
                partner_ids = Partner.search([
                    ('partner_weight', '>', 0),
                    ('partner_latitude', '>', latitude - 2), ('partner_latitude', '<', latitude + 2),
                    ('partner_longitude', '>', longitude - 1.5), ('partner_longitude', '<', longitude + 1.5),
                    ('country_id', '=', lead.country_id.id),
                    ('id', 'not in', lead.partner_declined_ids.mapped('id')),
                ])

                # 2. second way: in the same country, big area
                if not partner_ids:
                    partner_ids = Partner.search([
                        ('partner_weight', '>', 0),
                        ('partner_latitude', '>', latitude - 4), ('partner_latitude', '<', latitude + 4),
                        ('partner_longitude', '>', longitude - 3), ('partner_longitude', '<', longitude + 3),
                        ('country_id', '=', lead.country_id.id),
                        ('id', 'not in', lead.partner_declined_ids.mapped('id')),
                    ])

                # 3. third way: in the same country, extra large area
                if not partner_ids:
                    partner_ids = Partner.search([
                        ('partner_weight', '>', 0),
                        ('partner_latitude', '>', latitude - 8), ('partner_latitude', '<', latitude + 8),
                        ('partner_longitude', '>', longitude - 8), ('partner_longitude', '<', longitude + 8),
                        ('country_id', '=', lead.country_id.id),
                        ('id', 'not in', lead.partner_declined_ids.mapped('id')),
                    ])

                # 5. fifth way: anywhere in same country
                if not partner_ids:
                    # still haven't found any, let's take all partners in the country!
                    partner_ids = Partner.search([
                        ('partner_weight', '>', 0),
                        ('country_id', '=', lead.country_id.id),
                        ('id', 'not in', lead.partner_declined_ids.mapped('id')),
                    ])

                # 6. sixth way: closest partner whatsoever, just to have at least one result
                if not partner_ids:
                    # warning: point() type takes (longitude, latitude) as parameters in this order!
                    self._cr.execute("""SELECT id, distance
                                  FROM  (select id, (point(partner_longitude, partner_latitude) <-> point(%s,%s)) AS distance FROM res_partner
                                  WHERE active
                                        AND partner_longitude is not null
                                        AND partner_latitude is not null
                                        AND partner_weight > 0
                                        AND id not in (select partner_id from crm_lead_declined_partner where lead_id = %s)
                                        ) AS d
                                  ORDER BY distance LIMIT 1""", (longitude, latitude, lead.id))
                    res = self._cr.dictfetchone()
                    if res:
                        partner_ids = Partner.browse([res['id']])

                total_weight = 0
                toassign = []
                for partner in partner_ids:
                    total_weight += partner.partner_weight
                    toassign.append((partner.id, total_weight))

                random.shuffle(toassign)  # avoid always giving the leads to the first ones in db natural order!
                nearest_weight = random.randint(0, total_weight)
                for partner_id, weight in toassign:
                    if nearest_weight <= weight:
                        res_partner_ids[lead.id] = partner_id
                        break
        return res_partner_ids

    @api.multi
    def partner_interested(self, comment=False):
        message = _('<p>I am interested by this lead.</p>')
        if comment:
            message += '<p>%s</p>' % comment
        for lead in self:
            lead.message_post(body=message, subtype="mail.mt_note")
            lead.sudo().convert_opportunity(lead.partner_id.id)  # sudo required to convert partner data

    @api.multi
    def partner_desinterested(self, comment=False, contacted=False, spam=False):
        if contacted:
            message = '<p>%s</p>' % _('I am not interested by this lead. I contacted the lead.')
        else:
            message = '<p>%s</p>' % _('I am not interested by this lead. I have not contacted the lead.')
        partner_ids = self.env['res.partner'].search(
            [('id', 'child_of', self.env.user.partner_id.commercial_partner_id.id)])
        self.message_unsubscribe(partner_ids=partner_ids.ids)
        if comment:
            message += '<p>%s</p>' % comment
        self.message_post(body=message, subtype="mail.mt_note")
        values = {
            'partner_assigned_id': False,
        }

        if spam:
            tag_spam = self.env.ref('website_crm_partner_assign.tag_portal_lead_is_spam', False)
            if tag_spam and tag_spam not in self.tag_ids:
                values['tag_ids'] = [(4, tag_spam.id, False)]
        if partner_ids:
            values['partner_declined_ids'] = [(4, p, 0) for p in partner_ids.ids]
        self.sudo().write(values)

    @api.multi
    def update_lead_portal(self, values):
        self.check_access_rights('write')
        for lead in self:
            lead_values = {
                'planned_revenue': values['planned_revenue'],
                'probability': values['probability'],
                'priority': values['priority'],
                'date_deadline': values['date_deadline'] or False,
            }
            # As activities may belong to several users, only the current portal user activity
            # will be modified by the portal form. If no activity exist we create a new one instead
            # that we assign to the portal user.

            user_activity = lead.activity_ids.filtered(lambda activity: activity.user_id == self.env.user)[:1]
            if values['activity_date_deadline']:
                if user_activity:
                    user_activity.sudo().write({
                        'activity_type_id': values['activity_type_id'],
                        'summary': values['activity_summary'],
                        'date_deadline': values['activity_date_deadline'],
                    })
                else:
                    self.env['mail.activity'].sudo().create({
                        'res_model_id': self.env.ref('crm.model_crm_lead').id,
                        'res_id': lead.id,
                        'user_id': self.env.user.id,
                        'activity_type_id': values['activity_type_id'],
                        'summary': values['activity_summary'],
                        'date_deadline': values['activity_date_deadline'],
                    })
            lead.write(lead_values)

    @api.model
    def create_opp_portal(self, values):
        if self.env.user.partner_id.grade_id or self.env.user.commercial_partner_id.grade_id:
            user = self.env.user
            self = self.sudo()
        if not (values['contact_name'] and values['description'] and values['title']):
            return {
                'errors': _('All fields are required !')
            }
        tag_own = self.env.ref('website_crm_partner_assign.tag_portal_lead_own_opp', False)
        values = {
            'contact_name': values['contact_name'],
            'name': values['title'],
            'description': values['description'],
            'priority': '2',
            'partner_assigned_id': user.partner_id.id,
        }
        if tag_own:
            values['tag_ids'] = [(4, tag_own.id, False)]

        lead = self.create(values)
        lead.assign_salesman_of_assigned_partner()
        lead.convert_opportunity(lead.partner_id.id)
        return {
            'id': lead.id
        }
