##############################################################################
#
# Copyright (c) 2004-2008 TINY SPRL. (http://tiny.be) All Rights Reserved.
#
# $Id$
#
# WARNING: This program as such is intended to be used by professional
# programmers who take the whole responsability of assessing all potential
# consequences resulting from its eventual inadequacies and bugs
# End users who are looking for a ready-to-use solution with commercial
# garantees and support are strongly adviced to contract a Free Software
# Service Company
#
# This program is Free Software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License
# as published by the Free Software Foundation; either version 2
# of the License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place - Suite 330, Boston, MA  02111-1307, USA.
#
##############################################################################

import time
from osv import fields,osv


#
# Sale/Purchase Canal, Media
#
class res_partner_canal(osv.osv):
	_name = "res.partner.canal"
	_description = "Channels"
	_columns = {
		'name': fields.char('Channel Name',size=64, required=True),
		'active': fields.boolean('Active'),
	}
	_defaults = {
		'active': lambda *a: 1,
	}
res_partner_canal()

#
# Partner: State of Mind
#
class res_partner_som(osv.osv):
	_name = "res.partner.som"
	_columns = {
		'name': fields.char('State of Mind',size=64, required=True),
		'factor': fields.float('Factor', required=True)
	}
res_partner_som()

def _links_get(self, cr, uid, context={}):
	obj = self.pool.get('res.request.link')
	ids = obj.search(cr, uid, [])
	res = obj.read(cr, uid, ids, ['object', 'name'], context)
	return [(r['object'], r['name']) for r in res]

class res_partner_event(osv.osv):
	_name = "res.partner.event"
	_columns = {
		'name': fields.char('Events',size=64, required=True),
		'som': fields.many2one('res.partner.som', 'State of Mind'),
		'description': fields.text('Description'),
		'planned_cost': fields.float('Planned Cost'),
		'planned_revenue': fields.float('Planned Revenue'),
		'probability': fields.float('Probability (0.50)'),
		'document': fields.reference('Document', selection=_links_get, size=128),
		'partner_id': fields.many2one('res.partner', 'Partner', select=True),
		'date': fields.datetime('Date', size=16),
		'user_id': fields.many2one('res.users', 'User'),
		'canal_id': fields.many2one('res.partner.canal', 'Channel'),
		'partner_type': fields.selection([('customer','Customer'),('retailer','Retailer'),('prospect','Commercial Prospect')], 'Partner Relation'),
		'type': fields.selection([('sale','Sale Opportunity'),('purchase','Purchase Offer'),('prospect','Prospect Contact')], 'Type of Event'),
		'event_ical_id': fields.char('iCal id', size=64),
	}
	_order = 'date desc'
	_defaults = {
		'date': lambda *a: time.strftime('%Y-%m-%d %H:%M:%S'),
	}
res_partner_event()


class res_partner_event_type(osv.osv):
	_name = "res.partner.event.type"
	_description = "Partner Events"
	_columns = {
		'name': fields.char('Event Type',size=64, required=True),
		'key': fields.char('Key', size=64, required=True),
		'active': fields.boolean('Active'),
	}
	_defaults = {
		'active': lambda *a: 1
	}
	def check(self, cr, uid, key, context={}):
		return self.search(cr, uid, [('key','=',key)])
res_partner_event_type()


