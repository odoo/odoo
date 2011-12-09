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
            cr.execute("ALTER SEQUENCE " + self._sequence + " RESTART WITH " + str(last_sequence))


res_partner_location()

class res_partner_address(osv.osv):
    _name = 'res.partner.address'
    _inherits = { 'res.partner.location' : 'location_id' }

    _columns = {
        'location_id' : fields.many2one('res.partner.location', 'Location'),
        'contact_id' : fields.many2one('res.partner.contact', 'Contact'),

        'contact_firstname' : fields.related('contact_id', 'first_name', type='char', size=64, string='FirstName'),
        'name' : fields.related('contact_id', 'name', type='char', size='64', string="LastName"),
        'function': fields.char('Partner Function', size=64, help="Function of this contact with this partner"),
        'date_start': fields.date('Date Start',help="Start date of job(Joining Date)"),
        'date_stop': fields.date('Date Stop', help="Last date of job"),
        'state': fields.selection([('past', 'Past'),('current', 'Current')], \
                                  'State', required=True, help="Status of Address"),
    }

    _description ='Contact Partner Function'

    _defaults = {
        'state': 'current',
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
            cr.execute("UPDATE res_partner_address SET location_id = id")

res_partner_address()

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
