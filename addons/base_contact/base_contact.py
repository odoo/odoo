# -*- encoding: utf-8 -*-
##############################################################################
#
# Copyright (c) 2007 TINY SPRL. (http://tiny.be) All Rights Reserved.
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

import netsvc
from osv import fields, osv


class res_partner_contact(osv.osv):
    _name = "res.partner.contact"
    _description = "res.partner.contact"

    def _title_get(self,cr, user, context={}):
        obj = self.pool.get('res.partner.title')
        ids = obj.search(cr, user, [])
        res = obj.read(cr, user, ids, ['shortcut', 'name','domain'], context)
        res = [(r['shortcut'], r['name']) for r in res if r['domain']=='contact']
        return res

    _columns = {
        'name': fields.char('Last Name', size=30,required=True),
        'first_name': fields.char('First Name', size=30),
        'mobile':fields.char('Mobile',size=30),
        'title': fields.selection(_title_get, 'Title'),
        'website':fields.char('Website',size=120),
        'lang_id':fields.many2one('res.lang','Language'),
        'job_ids':fields.one2many('res.partner.job','contact_id','Functions'),
        'country_id':fields.many2one('res.country','Nationality'),
        'birthdate':fields.date('Birth Date'),
        'active' : fields.boolean('Active'),
    }
    _defaults = {
        'active' : lambda *a: True,
    }
    def name_get(self, cr, user, ids, context={}):
        #will return name and first_name.......
        if not len(ids):
            return []
        res = []
        for r in self.read(cr, user, ids, ['name','first_name','title']):
            addr = r['title'] and str(r['title'])+" " or ''
            addr +=str(r['name'] or '')
            if r['name'] and r['first_name']:
                addr += ' '
            addr += str(r['first_name'] or '')
            res.append((r['id'], addr))
        return res
res_partner_contact()

class res_partner_address(osv.osv):

    #overriding of the name_get defined in base in order to remove the old contact name
    def name_get(self, cr, user, ids, context={}):
        if not len(ids):
            return []
        res = []
        for r in self.read(cr, user, ids, ['zip','city','partner_id', 'street']):
            if context.get('contact_display', 'contact')=='partner':
                res.append((r['id'], r['partner_id'][1]))
            else:
                addr = str('')
                addr += str(r['street'] or '') + ' ' + str(r['zip'] or '') + ' ' + str(r['city'] or '')
                res.append((r['id'], addr.strip() or '/'))
        return res

    _name = 'res.partner.address'
    _inherit='res.partner.address'
    _description ='Partner Address'
    _columns = {
        'job_ids':fields.one2many('res.partner.job', 'address_id', 'Contacts'),
        'email': fields.related('job_ids', 'email', type='char', string='Default Email'),
    }
res_partner_address()

class res_partner_job(osv.osv):

    def _get_partner_id(self, cr, uid, ids, *a):
        res={}
        for id in self.browse(cr, uid, ids):
            res[id.id] = id.address_id.partner_id and id.address_id.partner_id.id or False
        return res

    def name_get(self, cr, uid, ids, context={}):
        if not len(ids):
            return []
        res = []
        for r in self.browse(cr, uid, ids):
            res.append((r.id, self.pool.get('res.partner.contact').name_get(cr, uid, [r.contact_id.id])[0][1] +", "+ r.function_id.name))
        return res

    def search(self, cr, user, args, offset=0, limit=None, order=None,
            context=None, count=False):
        for arg in args:
            if arg[0]=='address_id':
                self._order = 'sequence_partner'
            if arg[0]=='contact_id':
                self._order = 'sequence_contact'
        return super(res_partner_job,self).search(cr, user, args, offset, limit, order, context, count)

    _name = 'res.partner.job'
    _description ='Contact Function'
    _order = 'sequence_contact'
    _columns = {
        'name': fields.function(_get_partner_id, method=True, type='many2one', relation='res.partner', string='Partner'),
        'address_id':fields.many2one('res.partner.address','Address', required=True),
        'contact_id':fields.many2one('res.partner.contact','Contact', required=True),
        'function_id': fields.many2one('res.partner.function','Function', required=True),
        'sequence_contact':fields.integer('Sequence (Contact)',help='order of importance of this address in the list of addresses of the linked contact'),
        'sequence_partner':fields.integer('Sequence (Partner)',help='order of importance of this function in the list of functions of the linked partner'),
        'email': fields.char('E-Mail', size=240),
        'phone': fields.char('Phone', size=64),
        'date_start' : fields.date('Date Start'),
        'date_stop' : fields.date('Date Stop'),
        'state' : fields.selection([('past', 'Past'),('current', 'Current')], 'State', required=True),
    }

    _defaults = {
        'sequence_contact' : lambda *a: 0,
        'state' : lambda *a: 'current', 
    }
res_partner_job()


# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:

