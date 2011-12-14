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
        'job_ids': fields.one2many('res.partner.address', 'location2_id', 'Contacts'),
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
        'location2_id' : fields.many2one('res.partner.location', 'Location'),
        'contact_id' : fields.many2one('res.partner.contact', 'Contact', required=True),

        'partner_id' : fields.many2one('res.partner', 'Partner'),
        'contact_firstname' : fields.related('contact_id', 'first_name', type='char', size=64, string='Firstname'),
        'contact_name' : fields.related('contact_id', 'name', type='char', size='64', string="Lastname"),
        'function': fields.char('Partner Function', size=64, help="Function of this contact with this partner"),
        'date_start': fields.date('Date Start',help="Start date of job(Joining Date)"),
        'date_stop': fields.date('Date Stop', help="Last date of job"),
        'state': fields.selection([('past', 'Past'),('current', 'Current')], \
                                  'State', required=True, help="Status of Address"),
    }

    def name_get(self, cr, uid, ids, context=None):
        result = []

        append_call = result.append
        for obj in self.browse(cr, uid, ids, context=context):
            append_call((obj.id, "%s, %s" % (obj.contact_id.name_get()[0][1], obj.location_id.name_get()[0][1],)))
        return result


    _description ='Contact Partner Function'

    _defaults = {
        'state': 'current',
    }

    def create(self, cr, uid, values, context=None):
        record_id = super(res_partner_address, self).create(cr, uid, values, context=context)
        record = self.browse(cr, uid, record_id, context=context)
        if not record.partner_id and record.location2_id and record.location2_id.partner_id:
            record.write({'partner_id' : record.location2_id.partner_id.id}, context=context)
        return record_id

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
            cr.execute("UPDATE res_partner_address SET location_id = id, location2_id = id")

            contact_proxy = self.pool.get('res.partner.contact')
            uid = 1

            cr.execute("SELECT id, name, mobile, country_id, partner_id, phone, email, street, street2, city, company_id, state_id, zip, location_id \
                       FROM res_partner_address \
                       WHERE contact_id IS NULL AND name IS NOT NULL AND location_id IS NOT NULL")
            for item in cr.fetchall():

                values = {
                    'name' : item[1],
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

res_partner_address()

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
