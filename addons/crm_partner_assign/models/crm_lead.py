# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import random
from openerp import api, fields, models, _
from openerp.exceptions import UserError
from openerp.addons.base_geolocalize.models.res_partner import geo_find, geo_query_address


class CrmLead(models.Model):
    _inherit = 'crm.lead'

    partner_latitude = fields.Float(string='Geo Latitude', digits=(16, 5))
    partner_longitude = fields.Float(string='Geo Longitude', digits=(16, 5))
    partner_assigned_id = fields.Many2one('res.partner', string='Assigned Partner',
                                          track_visibility='onchange',
                                          index=True,
                                          help="Partner this case has been forwarded/assigned to.")
    date_assign = fields.Date(string='Assignation Date',
                              help="Last date this case was forwarded/assigned to a partner")

    @api.onchange('partner_assigned_id')
    def onchange_assign_id(self):
        """This function updates the "assignation date" automatically,
           when manually assign a partner in the geo assign tab"""
        self.date_assign = fields.Date.context_today(self)
        self.user_id = self.partner_assigned_id.user_id.id

    def get_interested_action(self, interested):
        try:
            LeadChannelAct = self.env.ref('crm_partner_assign.crm_lead_channel_interested_act')
        except ValueError:
            raise UserError(_("The CRM Channel Interested Action is missing"))
        action = LeadChannelAct.read()[0]
        action_context = eval(action['context'])
        action_context['interested'] = interested
        action['context'] = str(action_context)
        return action

    @api.multi
    def case_interested(self):
        self.ensure_one()
        return self.get_interested_action(True)

    @api.multi
    def case_disinterested(self):
        self.ensure_one()
        return self.get_interested_action(False)

    @api.multi
    def assign_salesman_of_assigned_partner(self):
        for lead in self.filtered(lambda x: x.partner_assigned_id.user_id != x.user_id and x.stage_id.probability > 0 and x.stage_id.probability < 100 or x.stage_id.sequence == 1):
            salesman_id = lead.partner_assigned_id.user_id.id
            salesteam_id = self.on_change_user(salesman_id)['value'].get('team_id')
            lead.write({'user_id': salesman_id, 'team_id': salesteam_id})

    @api.model
    def _merge_data(self, oldest, fields):
        fields += ['partner_latitude', 'partner_longitude',
                   'partner_assigned_id', 'date_assign']
        return super(CrmLead, self)._merge_data(oldest, fields)

    @api.multi
    def action_assign_partner(self):
        partner_dict = self.search_geo_partner()
        for lead in self:
            partner = partner_dict.get(lead.id, False)
            if not partner:
                continue
            if not lead.partner_latitude or not lead.partner_longitude:
                lead.assign_geo_localize()
            if partner.user_id:
                lead.allocate_salesman([partner.user_id.id], team_id=partner.team_id.id)
            lead.write({
                'date_assign': fields.Date.context_today(self),
                'partner_assigned_id': partner.id
            })

    @api.multi
    def assign_geo_localize(self):
        for lead in self:
            result = geo_find(geo_query_address(street=lead.street,
                                                zip=lead.zip,
                                                city=lead.city,
                                                state=lead.state_id.name,
                                                country=lead.country_id.name))
            if result:
                lead.write({'partner_latitude': result[0], 'partner_longitude': result[1]})

    def search_geo_partner(self):
        ResPartner = self.env['res.partner']
        res = {}
        for lead in self.filtered(lambda x: x.country_id):
            if not lead.partner_latitude or not lead.partner_longitude:
                lead.assign_geo_localize()
            Partners = ResPartner.search_geo_localize_partner(lead.partner_latitude,
                                                              lead.partner_longitude,
                                                              lead.country_id)
            total_weight = 0
            toassign = []
            for partner in Partners:
                total_weight += partner.partner_weight
                toassign.append((partner, total_weight))

            # avoid always giving the leads to the first ones in db natural
            # order!
            random.shuffle(toassign)
            nearest_weight = random.randint(0, total_weight)
            for partner, weight in toassign:
                if nearest_weight <= weight:
                    res[lead.id] = partner
                    break
        return res
