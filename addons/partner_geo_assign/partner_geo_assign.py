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

def geo_find(addr):
    import urllib,re
    regex = '<coordinates>([+-]?[0-9\.]+),([+-]?[0-9\.]+),([+-]?[0-9\.]+)</coordinates>'
    url = 'http://maps.google.com/maps/geo?q=' + urllib.quote(addr) + '&output=xml&oe=utf8&sensor=false'
    xml = urllib.urlopen(url).read()
    if '<error>' in xml:
        print 'Error'
        return None
    result = re.search(regex, xml, re.M|re.I)
    if not result:
        print 'No Regex', xml
        return None
    return float(result.group(1)),float(result.group(2))

class res_partner(osv.osv):
    _inherit = "res.partner"
    _columns = {
        'partner_latitude': fields.float('Geo Latitude', digits=(16,2)),
        'partner_longitude': fields.float('Geo Longitude', digits=(16,2)),
        'partner_weight': fields.integer('Weight',
            help="Gives the probability to assign a lead to this partner. (0 means no assignation.)"),
    }
    _defaults = {
        'partner_weight': lambda *args: 0
    }
    def geo_localize(self, cr, uid, ids, context=None):
        regex = '<coordinates>([+-]?[0-9\.]+),([+-]?[0-9\.]+),([+-]?[0-9\.]+)</coordinates>'
        for partner in self.browse(cr, uid, ids, context=context):
            part = partner.address[0]
            addr = ', '.join(filter(None, [part.street, part.street2, (part.zip or '')+' '+(part.city or ''), part.state_id and part.state_id.name, part.country_id and part.country_id.name]))
            result = geo_find(addr)
            if result:
                print 'Write', {
                    'partner_latitude': result[0],
                    'partner_longitude': result[1]
                }
                self.write(cr, uid, [partner.id], {
                    'partner_latitude': result[0],
                    'partner_longitude': result[1]
                }, context=context)
        return True
res_partner()

class crm_lead(osv.osv):
    _inherit = "crm.lead"
    _columns = {
        'partner_latitude': fields.float('Geo Latitude', digits=(16,2)),
        'partner_longitude': fields.float('Geo Longitude', digits=(16,2)),
        'partner_assigned_id': fields.many2one('res.partner','Assigned Partner')
        'date_assign': fields.date('Assignation Date')
    }
    def assign_partner(self, cr, uid, ids, context=None):
        for part in self.browse(cr, uid, ids, context=context):
            if not part.country_id:
                continue
            addr = ', '.join(filter(None, [part.street, part.street2, (part.zip or '')+' '+(part.city or ''), part.state_id and part.state_id.name, part.country_id and part.country_id.name]))
            result = geo_find(addr)
            if result:
                self.write(cr, uid, [part.id], {
                    'partner_latitude': result[0],
                    'partner_longitude': result[1]
                }, context=context)
                
                part_ids = self.pool.get('res.partner').search(cr, uid, [
                    ('partner_weight','>',0),
                    ('partner_latitude','>',result[0]-2), ('partner_latitude','<',result[0]+2),
                    ('partner_longitude','>',result[1]-1.5), ('partner_longitude','<',result[1]+1.5)
                ], context=context)
                if not part_ids:
                    part_ids = self.pool.get('res.partner').search(cr, uid, [
                        ('partner_weight','>',0),
                        ('partner_latitude','>',result[0]-4), ('partner_latitude','<',result[0]+4),
                        ('partner_longitude','>',result[1]-3), ('partner_longitude','<',result[1]+3)
                    ], context=context)
                total = 0
                toassign = []
                for part2 in self.pool.get('res.partner').browse(cr, uid, part_ids, context=context):
                    total += part2.partner_weight
                    toassign.append( (part2.id, total) )
                mypartner = random.randint(0,total)
                for t in toassign:
                    if mypartner<=t[1]:
                        self.write(cr, uid, [part.id], {'partner_assigned_id': t[0], 'date_assign': time.strftime('%Y-%m-%d')}, context=context)
                        break
        return True
crm_lead()

