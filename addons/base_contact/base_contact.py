# -*- encoding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution	
#    Copyright (C) 2004-2009 Tiny SPRL (<http://tiny.be>). All Rights Reserved
#    $Id$
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
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
        'job_ids':fields.one2many('res.partner.job','contact_id','Functions and Addresses'),
        'country_id':fields.many2one('res.country','Nationality'),
        'birthdate':fields.date('Birth Date'),
        'active' : fields.boolean('Active'),
        'partner_id':fields.related('job_ids','address_id','partner_id',type='many2one', relation='res.partner', string='Main Employer'),
        'function_id':fields.related('job_ids','function_id',type='many2one', relation='res.partner.function', string='Main Function'),
        'job_id':fields.related('job_ids',type='many2one', relation='res.partner.job', string='Main Job'),
        'email': fields.char('E-Mail', size=240),
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
            addr += r.get('name', '')
            if r['name'] and r['first_name']:
                addr += ' '
            addr += (r.get('first_name', '') or '')
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
                addr += "%s %s %s" % ( r.get('street', '') or '', r.get('zip', '') or '', r.get('city', '') or '' )
                res.append((r['id'], addr.strip() or '/'))
        return res

    _name = 'res.partner.address'
    _inherit='res.partner.address'
    _description ='Partner Address'
    _columns = {
        'job_id':fields.related('job_ids','contact_id','job_id',type='many2one', relation='res.partner.job', string='Main Job'),
        'job_ids':fields.one2many('res.partner.job', 'address_id', 'Contacts'),
    }
res_partner_address()

class res_partner_job(osv.osv):

    def name_get(self, cr, uid, ids, context={}):
        if not len(ids):
            return []
        res = []
        for r in self.browse(cr, uid, ids):
            funct = r.function_id and (", " + r.function_id.name) or ""
            res.append((r.id, self.pool.get('res.partner.contact').name_get(cr, uid, [r.contact_id.id])[0][1] + funct ))
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
    _description ='Contact Partner Function'
    _order = 'sequence_contact'
    _columns = {
        'name': fields.related('address_id','partner_id', type='many2one', relation='res.partner', string='Partner'),
        'address_id':fields.many2one('res.partner.address','Address'),
        'contact_id':fields.many2one('res.partner.contact','Contact', required=True, ondelete='cascade'),
        'function_id': fields.many2one('res.partner.function','Partner Function'),
        'sequence_contact':fields.integer('Contact Seq.',help='Order of importance of this address in the list of addresses of the linked contact'),
        'sequence_partner':fields.integer('Partner Seq.',help='Order of importance of this job title in the list of job title of the linked partner'),
        'email': fields.char('E-Mail', size=240),
        'phone': fields.char('Phone', size=64),
        'fax': fields.char('Fax', size=64),
        'extension': fields.char('Extension', size=64, help='Internal/External extension phone number'),
        'other': fields.char('Other', size=64, help='Additional phone field'),
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

