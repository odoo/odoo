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

from osv import fields, osv
import addons

class res_partner_contact(osv.osv):
    """ Partner Contact """

    _name = "res.partner.contact"
    _description = "Contact"

    def _name_get_full(self, cr, uid, ids, prop, unknow_none, context=None):
        result = {}
        for rec in self.browse(cr, uid, ids, context=context):
            result[rec.id] = rec.last_name+' '+(rec.first_name or '')
        return result

    _columns = {
        'name': fields.function(_name_get_full, string='Name', size=64, type="char", store=True, select=True),
        'last_name': fields.char('Last Name', size=64, required=True),
        'first_name': fields.char('First Name', size=64),
        'mobile': fields.char('Mobile', size=64),
        'title': fields.many2one('res.partner.title','Title', domain=[('domain','=','contact')]),
        'website': fields.char('Website', size=120),
        'lang_id': fields.many2one('res.lang', 'Language'),
        'job_ids': fields.one2many('res.partner.address', 'contact_id', 'Functions and Addresses'),
        'country_id': fields.many2one('res.country','Nationality'),
        'birthdate': fields.date('Birth Date'),
        'active': fields.boolean('Active', help="If the active field is set to False,\
                 it will allow you to hide the partner contact without removing it."),
        'partner_id': fields.related('job_ids', 'partner_id', type='many2one',\
                         relation='res.partner', string='Main Employer'),
        'function': fields.related('job_ids', 'function', type='char', \
                                 string='Main Function'),
        'email': fields.char('E-Mail', size=240),
        'comment': fields.text('Notes', translate=True),
        'photo': fields.binary('Photo'),
    }

    def _get_photo(self, cr, uid, context=None):
        photo_path = addons.get_module_resource('base_contact', 'images', 'photo.png')
        return open(photo_path, 'rb').read().encode('base64')

    _defaults = {
        'photo' : _get_photo,
        'active' : lambda *a: True,
    }

    _order = "name"

    def name_search(self, cr, uid, name='', args=None, operator='ilike', context=None, limit=None):
        if not args:
            args = []
        if context is None:
            context = {}
        if name:
            ids = self.search(cr, uid, ['|',('name', operator, name),('first_name', operator, name)] + args, limit=limit, context=context)
        else:
            ids = self.search(cr, uid, args, limit=limit, context=context)
        return self.name_get(cr, uid, ids, context=context)

    def name_get(self, cr, uid, ids, context=None):
        result = {}
        for obj in self.browse(cr, uid, ids, context=context):
            result[obj.id] = obj.name or '/'
            if obj.partner_id:
                result[obj.id] = result[obj.id] + ', ' + obj.partner_id.name
        return result.items()

    def _auto_init(self, cr, context=None):
        def table_exists(view_name):
            cr.execute('SELECT count(relname) FROM pg_class WHERE relname = %s', (view_name,))
            value = cr.fetchone()[0]
            return bool(value == 1)

        exists = table_exists(self._table)
        super(res_partner_contact, self)._auto_init(cr, context)

        if not exists:
            cr.execute("""
                INSERT INTO
                    res_partner_contact
                    (id,name,last_name,title,active)
                SELECT
                    id,COALESCE(name, '/'),COALESCE(name, '/'),title,true
                FROM
                    res_partner_address""")
            cr.execute("alter table res_partner_address add contact_id int references res_partner_contact")
            cr.execute("update res_partner_address set contact_id=id")
            cr.execute("select setval('res_partner_contact_id_seq', (select max(id)+1 from res_partner_contact))")

res_partner_contact()

class res_partner_location(osv.osv):
    _name = 'res.partner.location'
    _rec_name = 'street'
    _columns = {
        'street': fields.char('Street', size=128),
        'street2': fields.char('Street2', size=128),
        'zip': fields.char('Zip', change_default=True, size=24),
        'city': fields.char('City', size=128),
        'state_id': fields.many2one("res.country.state", 'Fed. State', domain="[('country_id','=',country_id)]"),
        'country_id': fields.many2one('res.country', 'Country'),
        'company_id': fields.many2one('res.company', 'Company',select=1),
        'job_ids': fields.one2many('res.partner.address', 'location_id', 'Contacts'),
        'partner_id': fields.related('job_ids', 'partner_id', type='many2one',\
                         relation='res.partner', string='Main Partner'),
    }
    _defaults = {
        'company_id': lambda s,cr,uid,c: s.pool.get('res.company')._company_default_get(cr, uid, 'res.partner.address', context=c),
    }
    def _auto_init(self, cr, context=None):
        def table_exists(view_name):
            cr.execute('SELECT count(relname) FROM pg_class WHERE relname = %s', (view_name,))
            value = cr.fetchone()[0]
            return bool(value == 1)

        exists = table_exists(self._table)
        super(res_partner_location, self)._auto_init(cr, context)

        if not exists:
            cr.execute("""
                INSERT INTO
                    res_partner_location
                    (id,street,street2,zip,city,
                     state_id,country_id,company_id)
                SELECT
                    id,street,street2,zip,city,
                    state_id,country_id,company_id
                FROM
                    res_partner_address""")
            cr.execute("alter table res_partner_address add location_id int references res_partner_location")
            cr.execute("update res_partner_address set location_id=id")
            cr.execute("select setval('res_partner_location_id_seq', (select max(id)+1 from res_partner_address))")

    def name_get(self, cr, uid, ids, context=None):
        result = {}
        for obj in self.browse(cr, uid, ids, context=context):
            res = []
            if obj.partner_id: res.append(obj.partner_id.name_get()[0][1])
            if obj.city: res.append(obj.city)
            if obj.country_id: res.append(obj.country_id.name_get()[0][1])
            result[obj.id] = ', '.join(res)
        return result.items()

res_partner_location()

class res_partner_address(osv.osv):
    _inherit = 'res.partner.address'

    def _default_location_id(self, cr, uid, context=None):
        if context is None:
            context = {}
        if not context.get('default_partner_id',False):
            return False
        ids = self.pool.get('res.partner.location').search(cr, uid, [('partner_id','=',context['default_partner_id'])], context=context)
        return ids and ids[0] or False

    def onchange_location_id(self,cr, uid, ids, location_id=False, context={}):
        if not location_id:
            return {}
        location = self.pool.get('res.partner.location').browse(cr, uid, location_id, context=context)
        return {'value':{
            'street': location.street,
            'street2': location.street2,
            'zip': location.zip,
            'city': location.city,
            'country_id': location.country_id and location.country_id.id or False,
            'state_id': location.state_id and location.state_id.id or False,
        }}

    _columns = {
        'location_id' : fields.many2one('res.partner.location', 'Location'),
        'contact_id' : fields.many2one('res.partner.contact', 'Contact'),

        # fields from location
        'street': fields.related('location_id', 'street', string='Street', type="char", store=True, size=128),
        'street2': fields.related('location_id', 'street2', string='Street2', type="char", store=True, size=128),
        'zip': fields.related('location_id', 'zip', string='Zip', type="char", store=True, change_default=True, size=24),
        'city': fields.related('location_id', 'city', string='City', type="char", store=True, size=128),
        'state_id': fields.related('location_id', 'state_id', relation="res.country.state", string='Fed. State', type="many2one", store=True, domain="[('country_id','=',country_id)]"),
        'country_id': fields.related('location_id', 'country_id', type='many2one', string='Country', store=True, relation='res.country'),

        'phone': fields.char('Phone', size=64),
        'fax': fields.char('Fax', size=64),
        'email': fields.char('E-Mail', size=240),

        # fields from contact
        'mobile' : fields.related('contact_id', 'mobile', type='char', size=64, string='Mobile'),
        'name' : fields.related('contact_id', 'name', type='char', size=64, string="Contact Name", store=True),
        'title' : fields.related('contact_id', 'title', type='many2one', relation='res.partner.title', string="Title", store=True),
    }
    def create(self, cr, uid, data, context={}):
        if not data.get('location_id', False):
            loc_id = self.pool.get('res.partner.location').create(cr, uid, {
                'street': data.get('street',''),
                'street2': data.get('street2',''),
                'zip': data.get('zip',''),
                'city': data.get('city',''),
                'country_id': data.get('country_id',False),
                'state_id': data.get('state_id',False)
            }, context=context)
            data['location_id'] = loc_id
        result = super(res_partner_address, self).create(cr, uid, data, context=context)
        return result

    def name_get(self, cr, uid, ids, context=None):
        result = {}
        for rec in self.browse(cr,uid, ids, context=context):
            res = []
            if rec.partner_id:
                res.append(rec.partner_id.name_get()[0][1])
            if rec.contact_id and rec.contact_id.name:
                res.append(rec.contact_id.name)
            if rec.location_id:
                if rec.location_id.city: res.append(rec.location_id.city)
                if rec.location_id.country_id: res.append(rec.location_id.country_id.name_get()[0][1])
            result[rec.id] = ', '.join(res)
        return result.items()

    _defaults = {
        'location_id': _default_location_id
    }

    def default_get(self, cr, uid, fields=[], context=None):
        if context is None:
            context = {}
        if 'default_type' in context:
            del context['default_type']
        return super(res_partner_address, self).default_get(cr, uid, fields, context)

res_partner_address()

