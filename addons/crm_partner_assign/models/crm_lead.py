# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import random

from odoo import api, fields, models, _
from odoo.exceptions import UserError
from odoo.addons.base_geolocalize.models.res_partner import geo_find, geo_query_address


class CrmLead(models.Model):
    _inherit = 'crm.lead'
    partner_latitude = fields.Float(string='Geo Latitude', digits=(16, 5))
    partner_longitude = fields.Float(string='Geo Longitude', digits=(16, 5))
    partner_assigned_id = fields.Many2one('res.partner', string='Assigned Partner', track_visibility='onchange', help="Partner this case has been forwarded/assigned to.", index=True)
    date_assign = fields.Date(string='Assignation Date', help="Last date this case was forwarded/assigned to a partner")

    def get_interested_action(self, interested):
        lead_channel_act = self.env.ref('crm_partner_assign.crm_lead_channel_interested_act', raise_if_not_found=False)
        if not lead_channel_act:
            raise UserError(_("The CRM Channel Interested Action is missing"))
        action = lead_channel_act.read()[0]
        action_context = eval(action['context'])
        action_context['interested'] = interested
        action['context'] = action_context
        return action
    
    @api.multi
    def case_interested(self):
        return self.get_interested_action(True)

    @api.multi
    def case_disinterested(self):
        return self.get_interested_action(False)
    
    @api.multi
    def assign_salesman_of_assigned_partner(self):
        for lead in self.filtered(lambda x: x.probability > 0 and x.probability < 100 and
            x.partner_assigned_id.user_id and x.partner_assigned_id.user_id != x.user_id):
            salesman_id = lead.partner_assigned_id.user_id.id
            salesteam_id = lead.on_change_user(salesman_id)['value'].get('team_id')
            lead.write({'user_id': salesman_id, 'team_id': salesteam_id})

    @api.multi
    def _merge_data(self, oldest, fields):
        fields += ['partner_latitude', 'partner_longitude', 'partner_assigned_id', 'date_assign']
        return super(CrmLead, self)._merge_data(oldest, fields)
 
    @api.onchange('partner_assigned_id')
    def onchange_assign_id(self):
        """This function updates the "assignation date" automatically, when manually assign a partner in the geo assign tab
        """
        if not self.partner_assigned_id:
            self.date_assign = False
        else:
            self.date_assign = fields.Date.context_today(self)
            self.user_id = self.partner_assigned_id.user_id.id

    @api.multi
    def action_assign_partner(self):

        partner_dict = self.search_geo_partner()
        for lead in self:
            partner = partner_dict.get(lead.id)
            if not partner:
                continue
            if not lead.partner_latitude or not lead.partner_longitude:
                lead.assign_geo_localize()
            if partner.user_id:
                lead.allocate_salesman(partner.user_id.ids, team_id=partner.team_id.id)
            lead.write({'date_assign': fields.Date.context_today(self), 
                       'partner_assigned_id': partner.id})

    @api.multi
    def assign_geo_localize(self):
        # Don't pass context to browse()! We need country name in english below
        for lead in self.with_context({}):
            result = geo_find(geo_query_address(street=lead.street,
                                                zip=lead.zip,
                                                city=lead.city,
                                                state=lead.state_id.name,
                                                country=lead.country_id.name))
            if result:
                lead.write({'partner_latitude': result[0], 'partner_longitude': result[1]})

    def search_geo_partner(self):
        ResPartner = self.env['res.partner']
        res_partners = {}
        for lead in self.filtered(lambda x: x.country_id):
            if not lead.partner_latitude or not lead.partner_longitude:
                lead.assign_geo_localize()
            partners = ResPartner.search_geo_localize_partner(lead.partner_latitude,
                                                               lead.partner_longitude,
                                                               lead.country_id)
            total_weight = 0
            toassign = []
            for partner in partners:
                total_weight += partner.partner_weight
                toassign.append((partner, total_weight))
            # avoid always giving the leads to the first ones in db natural order!
            random.shuffle(toassign) 
            nearest_weight = random.randint(0, total_weight)
            for partner, weight in toassign:
                if nearest_weight <= weight:
                    res_partners[lead.id] = partner
                    break
        return res_partners
