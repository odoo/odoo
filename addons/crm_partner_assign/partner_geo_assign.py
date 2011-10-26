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

from osv import osv
from osv import fields
import urllib,re
import random, time
from tools.translate import _
import tools

def geo_find(addr):
    addr = addr.encode('utf8')
    regex = '<coordinates>([+-]?[0-9\.]+),([+-]?[0-9\.]+),([+-]?[0-9\.]+)</coordinates>'
    url = 'http://maps.google.com/maps/geo?q=' + urllib.quote(addr) + '&output=xml&oe=utf8&sensor=false'
    try:
        xml = urllib.urlopen(url).read()
    except Exception, e:
        raise osv.except_osv(_('Network error'),
                             _('Could not contact geolocation servers, please make sure you have a working internet connection (%s)') % e)

    if '<error>' in xml:
        return None
    result = re.search(regex, xml, re.M|re.I)
    if not result:
        return None
    return float(result.group(2)),float(result.group(1))
    

class res_partner_grade(osv.osv):
    _order = 'sequence'
    _name = 'res.partner.grade'
    _columns = {
        'sequence': fields.integer('Sequence'),
        'active': fields.boolean('Active'),
        'name': fields.char('Grade Name', size=32)
    }
    _defaults = {
        'active': lambda *args: 1
    }
res_partner_grade()


class res_partner(osv.osv):
    _inherit = "res.partner"
    _columns = {
        'partner_latitude': fields.float('Geo Latitude'),
        'partner_longitude': fields.float('Geo Longitude'),
        'date_localization': fields.date('Geo Localization Date'),
        'partner_weight': fields.integer('Weight',
            help="Gives the probability to assign a lead to this partner. (0 means no assignation.)"),
        'opportunity_assigned_ids': fields.one2many('crm.lead', 'partner_assigned_id',\
            'Assigned Opportunities'),
        'grade_id': fields.many2one('res.partner.grade', 'Partner Grade')
    }
    _defaults = {
        'partner_weight': lambda *args: 0
    }
    def geo_localize(self, cr, uid, ids, context=None):
        for partner in self.browse(cr, uid, ids, context=context):
            if not partner.address:
                continue
            contact = partner.address[0] #TOFIX: should be get latitude and longitude for default contact?
            addr = ', '.join(filter(None, [
                    contact.street, 
                    "%s %s" % (contact.zip , contact.city), 
                    contact.state_id and contact.state_id.name, 
                    contact.country_id and contact.country_id.name]))
            result = geo_find(tools.ustr(addr))
            if result:
                self.write(cr, uid, [partner.id], {
                    'partner_latitude': result[0],
                    'partner_longitude': result[1],
                    'date_localization': time.strftime('%Y-%m-%d')
                }, context=context)
        return True
res_partner()

class crm_lead(osv.osv):
    _inherit = "crm.lead"
    _columns = {
        'partner_latitude': fields.float('Geo Latitude'),
        'partner_longitude': fields.float('Geo Longitude'),
        'partner_assigned_id': fields.many2one('res.partner', 'Assigned Partner', help="Partner this case has been forwarded/assigned to.", select=True),
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
                        {'date_assign': time.strftime('%Y-%m-%d'),
                         'user_id' : user_id}
                   }

    def assign_partner(self, cr, uid, ids, partner_id=False, context=None):
        partner_ids = {}
        res = False
        res_partner = self.pool.get('res.partner')
        if not partner_id:
            partner_ids = self.search_geo_partner(cr, uid, ids, context=context)
        for lead in self.browse(cr, uid, ids, context=context):
            if not partner_id:
                partner_id = partner_ids.get(lead.id, False)
            partner = res_partner.browse(cr, uid, partner_id, context=context)
            if partner.user_id:
                for lead_id in ids:
                    self.allocate_salesman(cr, uid, [lead_id], [partner.user_id.id], context=context)
            self.write(cr, uid, [lead.id], {'date_assign': time.strftime('%Y-%m-%d'), 'partner_assigned_id': partner_id}, context=context)
        return res
        

    def assign_geo_localize(self, cr, uid, ids, latitude=False, longitude=False, context=None):
        for lead in self.browse(cr, uid, ids, context=context):
            if not lead.country_id:
                continue
            addr = ', '.join(filter(None, [
                    lead.street, 
                    "%s %s" % (lead.zip, lead.city), 
                    lead.state_id and lead.state_id.name or '', 
                    lead.country_id and lead.country_id.name or ''
            ]))
            result = geo_find(tools.ustr(addr))
            if not latitude and result:
                latitude = result[0]
            if not longitude and result:
                longitude = result[1]
            self.write(cr, uid, [lead.id], {
                'partner_latitude': latitude,
                'partner_longitude': longitude
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
                    ('country', '=', lead.country_id.id),
                ], context=context)

                # 2. second way: in the same country, big area
                if not partner_ids:
                    partner_ids = res_partner.search(cr, uid, [
                        ('partner_weight', '>', 0),
                        ('partner_latitude', '>', latitude - 4), ('partner_latitude', '<', latitude + 4),
                        ('partner_longitude', '>', longitude - 3), ('partner_longitude', '<' , longitude + 3),
                        ('country', '=', lead.country_id.id),
                    ], context=context)


                # 5. fifth way: anywhere in same country
                if not partner_ids:
                    # still haven't found any, let's take all partners in the country!
                    partner_ids = partner.search(cr, uid, [
                        ('partner_weight', '>', 0),
                        ('country', '=', lead.country_id.id),
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
crm_lead()

