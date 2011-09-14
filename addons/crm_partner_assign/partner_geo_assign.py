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

def geo_find(addr):
    try: 
        regex = '<coordinates>([+-]?[0-9\.]+),([+-]?[0-9\.]+),([+-]?[0-9\.]+)</coordinates>'
        url = 'http://maps.google.com/maps/geo?q=' + urllib.quote(addr) + '&output=xml&oe=utf8&sensor=false'
        xml = urllib.urlopen(url).read()
        if '<error>' in xml:
            return None
        result = re.search(regex, xml, re.M|re.I)
        if not result:
            return None
        return float(result.group(1)),float(result.group(2))
    except Exception, e:
        raise osv.except_osv(_('Network error'), 
                             _('Could not contact geolocation servers, please make sure you have a working internet connection (%s)') % e)


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
        'partner_latitude': fields.float('Geo Longitude'),
        'partner_longitude': fields.float('Geo Latitude'),
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
            part = partner.address[0]
            addr = ', '.join(filter(None, [part.street, (part.zip or '')+' '+(part.city or ''), part.state_id and part.state_id.name, part.country_id and part.country_id.name]))
            result = geo_find(addr.encode('utf8'))
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
        'partner_latitude': fields.float('Geo Longitude'),
        'partner_longitude': fields.float('Geo Latitude'),
        'partner_assigned_id': fields.many2one('res.partner', 'Assigned Partner', help="Partner this case has been forwarded/assigned to.", select=True),
        'date_assign': fields.date('Assignation Date', help="Last date this case was forwarded/assigned to a partner"),
    }
    def onchange_assign_id(self, cr, uid, ids, partner_assigned_id, context=None):
        """This function updates the "assignation date" automatically, when manually assign a partner in the geo assign tab
            @param self: The object pointer
            @param cr: the current row, from the database cursor,
            @param uid: the current user’s ID for security checks,
            @param ids: List of stage’s IDs
            @stage_id: change state id on run time """

        if not partner_assigned_id:
            return {'value':{'date_assign': False}}
        else:
            return {'value':{'date_assign': time.strftime('%Y-%m-%d')}}

    def assign_partner(self, cr, uid, ids, context=None):
        ok = False
        for part in self.browse(cr, uid, ids, context=context):
            if not part.country_id:
                continue
            addr = ', '.join(filter(None, [part.street, (part.zip or '')+' '+(part.city or ''), part.state_id and part.state_id.name, part.country_id and part.country_id.name]))
            result = geo_find(addr.encode('utf8'))
            if result:
                self.write(cr, uid, [part.id], {
                    'partner_latitude': result[0],
                    'partner_longitude': result[1]
                }, context=context)

                # 1. first way: in the same country, small area
                part_ids = self.pool.get('res.partner').search(cr, uid, [
                    ('partner_weight','>',0),
                    ('partner_latitude','>',result[0]-2), ('partner_latitude','<',result[0]+2),
                    ('partner_longitude','>',result[1]-1.5), ('partner_longitude','<',result[1]+1.5),
                    ('country', '=', part.country_id.id),
                ], context=context)

                # 2. second way: in the same country, big area
                if not part_ids:
                    part_ids = self.pool.get('res.partner').search(cr, uid, [
                        ('partner_weight','>',0),
                        ('partner_latitude','>',result[0]-4), ('partner_latitude','<',result[0]+4),
                        ('partner_longitude','>',result[1]-3), ('partner_longitude','<',result[1]+3),
                        ('country', '=', part.country_id.id),
                    ], context=context)

                # 3. third way: other countries, small area
                if not part_ids:
                    part_ids = self.pool.get('res.partner').search(cr, uid, [
                        ('partner_weight','>',0),
                        ('partner_latitude','>',result[0]-2), ('partner_latitude','<',result[0]+2),
                        ('partner_longitude','>',result[1]-1.5), ('partner_longitude','<',result[1]+1.5)
                    ], context=context)

                # 4. fourth way: other countries, big area
                if not part_ids:
                    part_ids = self.pool.get('res.partner').search(cr, uid, [
                        ('partner_weight','>',0),
                        ('partner_latitude','>',result[0]-4), ('partner_latitude','<',result[0]+4),
                        ('partner_longitude','>',result[1]-3), ('partner_longitude','<',result[1]+3)
                    ], context=context)

                # 5. fifth way: anywhere in same country
                if not part_ids:
                    # still haven't found any, let's take all partners in the country!
                    part_ids = self.pool.get('res.partner').search(cr, uid, [
                        ('partner_weight','>',0),
                        ('country', '=', part.country_id.id),
                    ], context=context)

                # 6. sixth way: closest partner whatsoever, just to have at least one result    
                if not part_ids:
                    # warning: point() type takes (longitude, latitude) as parameters in this order!
                    cr.execute("""SELECT id, distance
                                  FROM  (select id, (point(partner_longitude, partner_latitude) <-> point(%s,%s)) AS distance FROM res_partner
                                  WHERE partner_longitude is not null
                                        AND partner_latitude is not null
                                        AND partner_weight > 0) AS d
                                  ORDER BY distance LIMIT 1""", (result[1],result[0]))
                    res = cr.dictfetchone()
                    if res:
                        part_ids.append(res['id'])

                total = 0
                toassign = []
                for part2 in self.pool.get('res.partner').browse(cr, uid, part_ids, context=context):
                    total += part2.partner_weight
                    toassign.append( (part2.id, total) )
                random.shuffle(toassign) # avoid always giving the leads to the first ones in db natural order!
                mypartner = random.randint(0,total)
                for t in toassign:
                    if mypartner<=t[1]:
                        self.write(cr, uid, [part.id], {'partner_assigned_id': t[0], 'date_assign': time.strftime('%Y-%m-%d')}, context=context)
                        break
            ok = True
        return ok
crm_lead()

