# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2004-2010 Tiny SPRL (<http://tiny.be>).
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################

import random

from openerp.addons.base_geolocalize.models.res_partner import geo_find, geo_query_address
from openerp.osv import osv
from openerp.osv import fields


class res_partner_grade(osv.osv):
    _order = 'sequence'
    _name = 'res.partner.grade'
    _columns = {
        'sequence': fields.integer('Sequence'),
        'active': fields.boolean('Active'),
        'name': fields.char('Grade Name'),
        'partner_weight': fields.integer('Grade Weight',
            help="Gives the probability to assign a lead to this partner. (0 means no assignation.)"),
    }
    _defaults = {
        'active': lambda *args: 1,
        'partner_weight':1
    }

class res_partner_activation(osv.osv):
    _name = 'res.partner.activation'
    _order = 'sequence'

    _columns = {
        'sequence' : fields.integer('Sequence'),
        'name' : fields.char('Name', required=True),
    }


class res_partner(osv.osv):
    _inherit = "res.partner"
    _columns = {
        'partner_weight': fields.integer('Grade Weight',
            help="Gives the probability to assign a lead to this partner. (0 means no assignation.)"),
        'opportunity_assigned_ids': fields.one2many('crm.lead', 'partner_assigned_id',\
            'Assigned Opportunities'),
        'grade_id': fields.many2one('res.partner.grade', 'Grade'),
        'activation' : fields.many2one('res.partner.activation', 'Activation', select=1),
        'date_partnership' : fields.date('Partnership Date'),
        'date_review' : fields.date('Latest Partner Review'),
        'date_review_next' : fields.date('Next Partner Review'),
        # customer implementation
        'assigned_partner_id': fields.many2one(
            'res.partner', 'Implemented by',
        ),
        'implemented_partner_ids': fields.one2many(
            'res.partner', 'assigned_partner_id',
            string='Implementation References',
        ),
    }
    _defaults = {
        'partner_weight': lambda *args: 0
    }
    
    def onchange_grade_id(self, cr, uid, ids, grade_id, context=None):
        res = {'value' :{'partner_weight':0}}
        if grade_id:
            partner_grade = self.pool.get('res.partner.grade').browse(cr, uid, grade_id)
            res['value']['partner_weight'] = partner_grade.partner_weight
        return res


class crm_lead(osv.osv):
    _inherit = "crm.lead"
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
                salesteam_id = partner.section_id and partner.section_id.id or False
                for lead_id in ids:
                    self.allocate_salesman(cr, uid, [lead_id], [partner.user_id.id], team_id=salesteam_id, context=context)
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
                                  WHERE partner_longitude is not null
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


# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
