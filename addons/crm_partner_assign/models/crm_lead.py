# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import random

from odoo import api, models, fields, _
from odoo.tools.safe_eval import safe_eval as eval
from odoo.exceptions import UserError

from odoo.addons.base_geolocalize.models.res_partner import geo_find, geo_query_address


class Lead(models.Model):
    _inherit = 'crm.lead'

    partner_latitude = fields.Float(string='Geo Latitude', digits=(16, 5))
    partner_longitude = fields.Float(string='Geo Longitude', digits=(16, 5))
    partner_assigned_id = fields.Many2one('res.partner', string='Assigned Partner',
        track_visibility='onchange', index=True,
        help="Partner this case has been forwarded/assigned to.")
    date_assign = fields.Date(string='Assignation Date',
        help="Last date this case was forwarded/assigned to a partner")

    @api.multi
    def _merge_data(self, oldest, fields):
        fields += ['partner_latitude', 'partner_longitude', 'partner_assigned_id', 'date_assign']
        return super(Lead, self)._merge_data(cr, oldest, fields)

    @api.onchange('partner_assigned_id')
    def _onchange_partner_assign_id(self):
        """This function updates the "assignation date" automatically, when manually assign a partner in the geo assign tab
        """

        if not self.partner_assigned_id:
            self.date_assign = False
        else:
            self.user_id = self.partner_assigned_id.user_id
            self.date_assign = fields.Date.context_today(self)

    @api.multi
    def action_assign_partner(self):
        return self.assign_partner(partner_id=False)

    @api.multi
    def assign_partner(self, partner_id=False):
        partners_dict = {}
        res = False
        Partner = self.env['res.partner']
        if not partner_id:
            partners_dict = self.search_geo_partner()
        for lead in self:
            partner_id = partner_id or partners_dict.get(lead.id)
            if not partner_id:
                continue
            lead.assign_geo_localize(lead.partner_latitude, lead.partner_longitude)
            partner = Partner.browse(partner_id)
            if partner.user_id:
                lead.allocate_salesman(partner.user_id.ids, team_id=partner.team_id.id)
            lead.write({'date_assign': fields.Date.context_today(lead), 'partner_assigned_id': partner_id})
        return res

    @api.multi
    def assign_geo_localize(self, latitude=False, longitude=False):
        if latitude and longitude:
            return self.write({
                'partner_latitude': latitude,
                'partner_longitude': longitude
            })
        # Don't pass context to self! We need country name in english below
        for lead in self.with_context({}).filtered(lambda lead:
                   (not lead.partner_latitude or not lead.partner_longitude)
                    and lead.country_id):
            result = geo_find(geo_query_address(street=lead.street,
                                                zip=lead.zip,
                                                city=lead.city,
                                                state=lead.state_id.name,
                                                country=lead.country_id.name))
            if result:
                lead.write({
                    'partner_latitude': result[0],
                    'partner_longitude': result[1]
                })
        return True

    @api.multi
    def search_geo_partner(self):
        Partner = self.env['res.partner']
        partners_dict = {}
        self.assign_geo_localize()
        for lead in self.filtered(lambda lead: lead.country_id):
            partners = Partner
            latitude = lead.partner_latitude
            longitude = lead.partner_longitude
            if latitude and longitude:
                # 1. first way: in the same country, small area
                partners = Partner.search([
                    ('partner_weight', '>', 0),
                    ('partner_latitude', '>', latitude - 2), ('partner_latitude', '<', latitude + 2),
                    ('partner_longitude', '>', longitude - 1.5), ('partner_longitude', '<', longitude + 1.5),
                    ('country_id', '=', lead.country_id.id),
                ])

                # 2. second way: in the same country, big area
                if not partners:
                    partners = Partner.search([
                        ('partner_weight', '>', 0),
                        ('partner_latitude', '>', latitude - 4), ('partner_latitude', '<', latitude + 4),
                        ('partner_longitude', '>', longitude - 3), ('partner_longitude', '<' , longitude + 3),
                        ('country_id', '=', lead.country_id.id),
                    ])

                # 3. third way: in the same country, extra large area
                if not partners:
                    partners = Partner.search([
                        ('partner_weight','>', 0),
                        ('partner_latitude','>', latitude - 8), ('partner_latitude','<', latitude + 8),
                        ('partner_longitude','>', longitude - 8), ('partner_longitude','<', longitude + 8),
                        ('country_id', '=', lead.country_id.id),
                    ])

                # 5. fifth way: anywhere in same country
                if not partners:
                    # still haven't found any, let's take all partners in the country!
                    partners = Partner.search([
                        ('partner_weight', '>', 0),
                        ('country_id', '=', lead.country_id.id),
                    ])

                # 6. sixth way: closest partner whatsoever, just to have at least one result
                if not partners:
                    # warning: point() type takes (longitude, latitude) as parameters in this order!
                    self._cr.execute("""SELECT id, distance
                                  FROM  (select id, (point(partner_longitude, partner_latitude) <-> point(%s,%s)) AS distance FROM res_partner
                                  WHERE active
                                        AND partner_longitude is not null
                                        AND partner_latitude is not null
                                        AND partner_weight > 0) AS d
                                  ORDER BY distance LIMIT 1""", (longitude, latitude))
                    res = self._cr.dictfetchone()
                    if res:
                        partners += Partner.browse(res['id'])

                total_weight = 0
                toassign = []
                for partner in partners:
                    total_weight += partner.partner_weight
                    toassign.append((partner.id, total_weight))

                random.shuffle(toassign) # avoid always giving the leads to the first ones in db natural order!
                nearest_weight = random.randint(0, total_weight)
                for partner_id, weight in toassign:
                    if nearest_weight <= weight:
                        partners_dict[lead.id] = partner_id
                        break
        return partners_dict

    def get_interested_action(self, interested):
        action = self.env.ref('crm_partner_assign.crm_lead_channel_interested_act', False)
        if not action:
            raise UserError(_("The CRM Channel Interested Action is missing"))
        [action] = action.read()
        action_context = eval(action['context'])
        action_context['interested'] = interested
        action['context'] = str(action_context)
        return action

    @api.multi
    def case_interested(self):
        return self.get_interested_action(True)

    @api.multi
    def case_disinterested(self):
        return self.get_interested_action(False)

    @api.multi
    def assign_salesman_of_assigned_partner(self):
        salesmans_leads = {}
        for lead in self:
            if (lead.stage_id.probability > 0 and lead.stage_id.probability < 100) or lead.stage_id.sequence == 1:
                if lead.partner_assigned_id.user_id and lead.partner_assigned_id.user_id != lead.user_id:
                    salesman_id = lead.partner_assigned_id.user_id.id
                    if salesmans_leads.get(salesman_id):
                        salesmans_leads[salesman_id].append(lead.id)
                    else:
                        salesmans_leads[salesman_id] = lead.ids
        for salesman_id, lead_ids in salesmans_leads.items():
            leads = self.browse(lead_ids)
            salesteam_id = leads.on_change_user(salesman_id)['value'].get('team_id')
            leads.write({'user_id': salesman_id, 'team_id': salesteam_id})

    @api.multi
    def set_tag_assign(self, assign):
        ASSIGNED = 'tag_portal_lead_assigned'
        RECYCLE = 'tag_portal_lead_recycle'
        tag_to_add_id = self.env.ref('crm_partner_assign.%s' % (assign and ASSIGNED or RECYCLE,)).id
        tag_to_rem_id = self.env.ref('crm_partner_assign.%s' % (assign and RECYCLE or ASSIGNED,)).id
        self.write({'tag_ids': [(3, tag_to_rem_id, False), (4, tag_to_add_id, False)]})
