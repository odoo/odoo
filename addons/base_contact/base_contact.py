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

    _columns = {
        'name': fields.char('Last Name', size=64, required=True),
        'first_name': fields.char('First Name', size=64),
        'mobile': fields.char('Mobile', size=64),
        'title': fields.many2one('res.partner.title','Title'),
        'website': fields.char('Website', size=120),
        'lang_id': fields.many2one('res.lang', 'Language'),
        'job_ids': fields.one2many('res.partner.address', 'contact_id', 'Functions and Addresses'),
        'country_id': fields.many2one('res.country','Nationality'),
        'birthdate': fields.date('Birth Date'),
        'active': fields.boolean('Active', help="If the active field is set to False,\
                 it will allow you to hide the partner contact without removing it."),
        'partner_id': fields.related('job_ids', 'location_id', 'partner_id', type='many2one',\
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

    _order = "name,first_name"

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
        return [
            (obj.id, " ".join(filter(None, [obj.first_name, obj.name])),)
            for obj in self.browse(cr, uid, ids, context=context)
        ]

res_partner_contact()

class res_partner(osv.osv):
    _inherit = 'res.partner'
    _columns = {
        'address': fields.one2many('res.partner.location', 'partner_id', 'Address')
    }
res_partner()

class res_partner_location(osv.osv):
    _name = 'res.partner.location'
    _inherit = 'res.partner.address'
    _columns = {
        'job_ids': fields.one2many('res.partner.address', 'location_id', 'Contacts'),
    }
    def _auto_init(self, cr, context=None):
        def table_exists(view_name):
            cr.execute('SELECT count(relname) FROM pg_class WHERE relname = %s', (view_name,))
            value = cr.fetchone()[0]
            return bool(value == 1)

        exists = table_exists(self._table)
        super(res_partner_location, self)._auto_init(cr, context)

        if not exists:
            sequence_name = self.pool.get('res.partner.address')._sequence
            cr.execute("SELECT last_value FROM " + sequence_name)
            last_sequence = cr.fetchone()[0]
            cr.execute("INSERT INTO res_partner_location SELECT * FROM res_partner_address")
            cr.execute("ALTER SEQUENCE " + self._sequence + " RESTART WITH " + str(last_sequence + 10))

    def name_get(self, cr, uid, ids, context=None):
        return [
            ((obj.id, "%s, %s" % (obj.city, obj.country_id and obj.country_id.name or '')))
            for obj in self.browse(cr, uid, ids, context=context)
        ]

res_partner_location()

class res_partner_address(osv.osv):
    _name = 'res.partner.address'
    _inherits = { 'res.partner.location' : 'location_id' }

    def _get_use_existing_address(self, cr, uid, ids, fieldnames, args, context=None):
        return dict(map(lambda x: (x, False), ids))

    def _set_use_existing_address(self, cr, uid, ids, name, value, arg, context=None):
        return True

    def _default_location_id(self, cr, uid, context=None):
        context = context or {}
        if not context.get('default_partner_id',False):
            return False
        ids = self.pool.get('res.partner.location').search(cr, uid, [('partner_id','=',context['default_partner_id'])], context=context)
        return ids and ids[0] or False

    def _default_existing_get(self, cr, uid, context=None):
        return bool(self._default_location_id(cr, uid, context))

    _columns = {
        'location_id' : fields.many2one('res.partner.location', 'Location'),
        'use_existing_address' : fields.function(_get_use_existing_address,
                                             fnct_inv=_set_use_existing_address,
                                             type='boolean',
                                             string='Link to Existing Address'),

        'contact_id' : fields.many2one('res.partner.contact', 'Contact'),

        # come modules are doing SQL reports on those fields (crm)
        'country_id': fields.related('location_id', 'country_id', type='many2one', string='Country', store=True, relation='res.country'),
        'company_id': fields.related('location_id', 'company_id', type='many2one', string='Company', store=True, relation='res.company'),

        # Do not use the one of the location, each job position has it's phone
        'phone': fields.char('Phone', size=64),
        'fax': fields.char('Fax', size=64),
        'email': fields.char('E-Mail', size=240),
        'function': fields.char('Partner Function', size=64, help="Function of this contact with this partner"),

        #'partner_id' : fields.related('location_id', 'partner_id', type="many2one", relation='res.partner', string='Partner'),
        'contact_firstname' : fields.related('contact_id', 'first_name', type='char', size=64, string='Firstname'),
        'contact_name' : fields.related('contact_id', 'name', type='char', size=64, string="Lastname"),
        'name' : fields.related('contact_id', 'name', type='char', size=64, string="Lastname", store=True),
    }

    def name_get(self, cr, uid, ids, context=None):
        return [
            ((obj.id, "%s, %s" % (obj.contact_id.name_get()[0][1], obj.location_id.name_get()[0][1],)))
            for obj in self.browse(cr, uid, ids, context=context)
        ]


    _defaults = {
        'use_existing_address': _default_existing_get,
        'location_id': _default_location_id
    }

    def _auto_init(self, cr, context=None):
        def column_exists(column):
            cr.execute("select count(attname) from pg_attribute where attrelid = \
                       (select oid from pg_class where relname = %s) \
                       and attname = %s", (self._table, column,))
            value = cr.fetchone()[0]
            return bool(value == 1)

        exists = column_exists('location_id')
        super(res_partner_address, self)._auto_init(cr, context)

        if not exists:
            contact_proxy = self.pool.get('res.partner.contact')
            uid = 1
            cr.execute("SELECT id, name, mobile, country_id, partner_id, phone, email, street, street2, city, company_id, state_id, zip, location_id \
                       FROM res_partner_address")
            for item in cr.fetchall():
                values = {
                    'name' : item[1] or '/',
                    'mobile' : item[2],
                    'country_id' : item[3],
                    'phone' : item[5],
                    'email' : item[6],
                    'company_id' : item[10],
                }

                contact_id = contact_proxy.create(cr, uid, values, context=context)
                values = {
                    'street' : item[7],
                    'street2' : item[8],
                    'city' : item[9],
                    'country_id' : item[3],
                    'company_id' : item[10],
                    'state_id' : item[11],
                    'zip' : item[12],
                }
                location_id = self.pool.get('res.partner.location').create(cr, uid, values, context=context)
                cr.execute("UPDATE res_partner_address SET location_id = %s, contact_id = %s, partner_id = %s WHERE id = %s",
                           (location_id, contact_id, item[4], item[0],))

    def default_get(self, cr, uid, fields=[], context=None):
        context = context or {}
        if 'default_type' in context:
            del context['default_type']
        return super(res_partner_address, self).default_get(cr, uid, fields, context)

res_partner_address()

