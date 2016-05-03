# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import random

from openerp.osv import osv, fields
from openerp.tools.translate import _
from openerp.tools.safe_eval import safe_eval as eval
from openerp.exceptions import UserError

from openerp.addons.base_geolocalize.models.res_partner import geo_find, geo_query_address

class crm_lead(osv.osv):
    _inherit = 'crm.lead'

    _columns = {
        'partner_latitude': fields.float('Geo Latitude', digits=(16, 5)),
        'partner_longitude': fields.float('Geo Longitude', digits=(16, 5)),
        'partner_assigned_id': fields.many2one('res.partner', 'Assigned Partner',track_visibility='onchange' , help="Partner this case has been forwarded/assigned to.", select=True),
        'date_assign': fields.date('Assignation Date', help="Last date this case was forwarded/assigned to a partner"),
    }

    def _merge_data(self, cr, uid, ids, oldest, fields, context=None):
        fields += ['partner_latitude', 'partner_longitude', 'partner_assigned_id', 'date_assign']
        return super(crm_lead, self)._merge_data(cr, uid, ids, oldest, fields, context=context)

    def onchange_assign_id(self, cr, uid, ids, partner_assigned_id, context=None):
        """This function updates the "assignation date" automatically, when manually assign a partner in the geo assign tab
        """

        if not partner_assigned_id:
            return {'value':{'date_assign': False}}
        else:
            partners = self.pool.get('res.partner').browse(cr, uid, [partner_assigned_id], context=context)
            user_id = partners[0] and partners[0].user_id.id or False
            return {'value':
                        {'date_assign': fields.date.context_today(self,cr,uid,context=context),
                         'user_id' : user_id}
                   }

    def action_assign_partner(self, cr, uid, ids, context=None):
        return self.assign_partner(cr, uid, ids, partner_id=False, context=context)

    def assign_partner(self, cr, uid, ids, partner_id=False, context=None):
        partner_ids = {}
        res = False
        res_partner = self.pool.get('res.partner')
        if not partner_id:
            partner_ids = self.search_geo_partner(cr, uid, ids, context=context)
        for lead in self.browse(cr, uid, ids, context=context):
            if not partner_id:
                partner_id = partner_ids.get(lead.id, False)
            if not partner_id:
                continue
            self.assign_geo_localize(cr, uid, [lead.id], lead.partner_latitude, lead.partner_longitude, context=context)
            partner = res_partner.browse(cr, uid, partner_id, context=context)
            if partner.user_id:
                salesteam_id = partner.team_id and partner.team_id.id or False
                self.allocate_salesman(cr, uid, [lead.id], [partner.user_id.id], team_id=salesteam_id, context=context)
            self.write(cr, uid, [lead.id], {'date_assign': fields.date.context_today(self,cr,uid,context=context), 'partner_assigned_id': partner_id}, context=context)
        return res

    def assign_geo_localize(self, cr, uid, ids, latitude=False, longitude=False, context=None):
        if latitude and longitude:
            self.write(cr, uid, ids, {
                'partner_latitude': latitude,
                'partner_longitude': longitude
            }, context=context)
            return True
        # Don't pass context to browse()! We need country name in english below
        for lead in self.browse(cr, uid, ids):
            if lead.partner_latitude and lead.partner_longitude:
                continue
            if lead.country_id:
                result = geo_find(geo_query_address(street=lead.street,
                                                    zip=lead.zip,
                                                    city=lead.city,
                                                    state=lead.state_id.name,
                                                    country=lead.country_id.name))
                if result:
                    self.write(cr, uid, [lead.id], {
                        'partner_latitude': result[0],
                        'partner_longitude': result[1]
                    }, context=context)
        return True

    def search_geo_partner(self, cr, uid, ids, context=None):
        res_partner = self.pool.get('res.partner')
        res_partner_ids = {}
        self.assign_geo_localize(cr, uid, ids, context=context)
        for lead in self.browse(cr, uid, ids, context=context):
            partner_ids = []
            if not lead.country_id:
                continue
            latitude = lead.partner_latitude
            longitude = lead.partner_longitude
            if latitude and longitude:
                # 1. first way: in the same country, small area
                partner_ids = res_partner.search(cr, uid, [
                    ('partner_weight', '>', 0),
                    ('partner_latitude', '>', latitude - 2), ('partner_latitude', '<', latitude + 2),
                    ('partner_longitude', '>', longitude - 1.5), ('partner_longitude', '<', longitude + 1.5),
                    ('country_id', '=', lead.country_id.id),
                ], context=context)

                # 2. second way: in the same country, big area
                if not partner_ids:
                    partner_ids = res_partner.search(cr, uid, [
                        ('partner_weight', '>', 0),
                        ('partner_latitude', '>', latitude - 4), ('partner_latitude', '<', latitude + 4),
                        ('partner_longitude', '>', longitude - 3), ('partner_longitude', '<' , longitude + 3),
                        ('country_id', '=', lead.country_id.id),
                    ], context=context)

                # 3. third way: in the same country, extra large area
                if not partner_ids:
                    partner_ids = res_partner.search(cr, uid, [
                        ('partner_weight','>', 0),
                        ('partner_latitude','>', latitude - 8), ('partner_latitude','<', latitude + 8),
                        ('partner_longitude','>', longitude - 8), ('partner_longitude','<', longitude + 8),
                        ('country_id', '=', lead.country_id.id),
                    ], context=context)

                # 5. fifth way: anywhere in same country
                if not partner_ids:
                    # still haven't found any, let's take all partners in the country!
                    partner_ids = res_partner.search(cr, uid, [
                        ('partner_weight', '>', 0),
                        ('country_id', '=', lead.country_id.id),
                    ], context=context)

                # 6. sixth way: closest partner whatsoever, just to have at least one result
                if not partner_ids:
                    # warning: point() type takes (longitude, latitude) as parameters in this order!
                    cr.execute("""SELECT id, distance
                                  FROM  (select id, (point(partner_longitude, partner_latitude) <-> point(%s,%s)) AS distance FROM res_partner
                                  WHERE active
                                        AND partner_longitude is not null
                                        AND partner_latitude is not null
                                        AND partner_weight > 0) AS d
                                  ORDER BY distance LIMIT 1""", (longitude, latitude))
                    res = cr.dictfetchone()
                    if res:
                        partner_ids.append(res['id'])

                total_weight = 0
                toassign = []
                for partner in res_partner.browse(cr, uid, partner_ids, context=context):
                    total_weight += partner.partner_weight
                    toassign.append( (partner.id, total_weight) )

                random.shuffle(toassign) # avoid always giving the leads to the first ones in db natural order!
                nearest_weight = random.randint(0, total_weight)
                for partner_id, weight in toassign:
                    if nearest_weight <= weight:
                        res_partner_ids[lead.id] = partner_id
                        break
        return res_partner_ids

    def get_interested_action(self, cr, uid, interested, context=None):
        try:
            model, action_id = self.pool.get('ir.model.data').get_object_reference(cr, uid, 'crm_partner_assign', 'crm_lead_channel_interested_act')
        except ValueError:
            raise UserError(_("The CRM Channel Interested Action is missing"))
        action = self.pool[model].read(cr, uid, [action_id], context=context)[0]
        action_context = eval(action['context'])
        action_context['interested'] = interested
        action['context'] = str(action_context)
        return action

    def case_interested(self, cr, uid, ids, context=None):
        return self.get_interested_action(cr, uid, True, context=context)

    def case_disinterested(self, cr, uid, ids, context=None):
        return self.get_interested_action(cr, uid, False, context=context)

    def assign_salesman_of_assigned_partner(self, cr, uid, ids, context=None):
        salesmans_leads = {}
        for lead in self.browse(cr, uid, ids, context=context):
            if (lead.stage_id.probability > 0 and lead.stage_id.probability < 100) or lead.stage_id.sequence == 1: 
                if lead.partner_assigned_id and lead.partner_assigned_id.user_id and lead.partner_assigned_id.user_id != lead.user_id:
                    salesman_id = lead.partner_assigned_id.user_id.id
                    if salesmans_leads.get(salesman_id):
                        salesmans_leads[salesman_id].append(lead.id)
                    else:
                        salesmans_leads[salesman_id] = [lead.id]
        for salesman_id, lead_ids in salesmans_leads.items():
            salesteam_id = self.on_change_user(cr, uid, lead_ids, salesman_id, context=None)['value'].get('team_id')
            self.write(cr, uid, lead_ids, {'user_id': salesman_id, 'team_id': salesteam_id}, context=context)

    def set_tag_assign(self, cr, uid, ids, assign, context=None):
        ASSIGNED = 'tag_portal_lead_assigned'
        RECYCLE = 'tag_portal_lead_recycle'
        tag_to_add = self.pool.get('ir.model.data').get_object_reference(cr, uid, 'crm_partner_assign', assign and ASSIGNED or RECYCLE)[1]
        tag_to_rem = self.pool.get('ir.model.data').get_object_reference(cr, uid, 'crm_partner_assign', assign and RECYCLE or ASSIGNED)[1]
        self.write(cr, uid, ids, {'tag_ids': [(3, tag_to_rem, False), (4, tag_to_add, False)]}, context=context)
