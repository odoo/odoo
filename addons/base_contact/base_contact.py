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

class res_partner_contact(osv.osv):
    """ Partner Contact """

    _name = "res.partner.contact"
    _description = "Contact"

    def _main_job(self, cr, uid, ids, fields, arg, context=None):
        """
            @param self: The object pointer
            @param cr: the current row, from the database cursor,
            @param uid: the current user’s ID for security checks,
            @param ids: List of partner contact’s IDs
            @fields: Get Fields
            @param context: A standard dictionary for contextual values
            @param arg: list of tuples of form [(‘name_of_the_field’, ‘operator’, value), ...]. """
        res = dict.fromkeys(ids, False)

        res_partner_job_obj = self.pool.get('res.partner.job')
        all_job_ids = res_partner_job_obj.search(cr, uid, [])
        all_job_names = dict(zip(all_job_ids, res_partner_job_obj.name_get(cr, uid, all_job_ids, context=context)))

        for contact in self.browse(cr, uid, ids, context=context):
            if contact.job_ids:
                res[contact.id] = all_job_names.get(contact.job_ids[0].id, False)

        return res

    _columns = {
        'name': fields.char('Last Name', size=64, required=True),
        'first_name': fields.char('First Name', size=64),
        'mobile': fields.char('Mobile', size=64),
        'title': fields.many2one('res.partner.title','Title'),
        'website': fields.char('Website', size=120),
        'lang_id': fields.many2one('res.lang', 'Language'),
        'job_ids': fields.one2many('res.partner.job', 'contact_id', 'Functions and Addresses'),
        'country_id': fields.many2one('res.country','Nationality'),
        'birthdate': fields.date('Birth Date'),
        'active': fields.boolean('Active', help="If the active field is set to False,\
                 it will allow you to hide the partner contact without removing it."),
        'partner_id': fields.related('job_ids', 'address_id', 'partner_id', type='many2one',\
                         relation='res.partner', string='Main Employer'),
        'function': fields.related('job_ids', 'function', type='char', \
                                 string='Main Function'),
        'job_id': fields.function(_main_job, method=True, type='many2one',\
                                 relation='res.partner.job', string='Main Job'),
        'email': fields.char('E-Mail', size=240),
        'comment': fields.text('Notes', translate=True),
        'photo': fields.binary('Image'),

    }
    _defaults = {
        'active' : lambda *a: True,
    }

    _order = "name,first_name"

    def name_get(self, cr, user, ids, context=None):

        """ will return name and first_name.......
            @param self: The object pointer
            @param cr: the current row, from the database cursor,
            @param user: the current user’s ID for security checks,
            @param ids: List of create menu’s IDs
            @return: name and first_name
            @param context: A standard dictionary for contextual values
        """

        if not len(ids):
            return []
        res = []
        for contact in self.browse(cr, user, ids, context=context):
            _contact = ""
            if contact.title:
                _contact += "%s "%(contact.title.name)
            _contact += contact.name or ""
            if contact.name and contact.first_name:
                _contact += " "
            _contact += contact.first_name or ""
            res.append((contact.id, _contact))
        return res
    
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


class res_partner_address(osv.osv):

    #overriding of the name_get defined in base in order to remove the old contact name
    def name_get(self, cr, user, ids, context=None):
        """
            @param self: The object pointer
            @param cr: the current row, from the database cursor,
            @param user: the current user,
            @param ids: List of partner address’s IDs
            @param context: A standard dictionary for contextual values
        """

        if not len(ids):
            return []
        res = []
        if context is None:
            context = {}
        for r in self.read(cr, user, ids, ['zip', 'city', 'partner_id', 'street']):
            if context.get('contact_display', 'contact')=='partner' and r['partner_id']:
                res.append((r['id'], r['partner_id'][1]))
            else:
                addr = "%s %s %s" % (r.get('street', '') or '', r.get('zip', '') \
                                    or '', r.get('city', '') or '')
                res.append((r['id'], addr.strip() or '/'))
        return res

    _name = 'res.partner.address'
    _inherit = 'res.partner.address'
    _description ='Partner Address'

    _columns = {
        'job_id': fields.related('job_ids','contact_id','job_id',type='many2one',\
                         relation='res.partner.job', string='Main Job'),
        'job_ids': fields.one2many('res.partner.job', 'address_id', 'Contacts'),
    }
res_partner_address()

class res_partner_job(osv.osv):
    def name_get(self, cr, uid, ids, context=None):
        """
            @param self: The object pointer
            @param cr: the current row, from the database cursor,
            @param user: the current user,
            @param ids: List of partner address’s IDs
            @param context: A standard dictionary for contextual values
        """
        if context is None:
            context = {}

        if not ids:
            return []
        res = []

        jobs = self.browse(cr, uid, ids, context=context)

        contact_ids = [rec.contact_id.id for rec in jobs]
        contact_names = dict(self.pool.get('res.partner.contact').name_get(cr, uid, contact_ids, context=context))

        for r in jobs:
            function_name = r.function
            funct = function_name and (", " + function_name) or ""
            res.append((r.id, contact_names.get(r.contact_id.id, '') + funct))

        return res

    _name = 'res.partner.job'
    _description ='Contact Partner Function'
    _order = 'sequence_contact'

    _columns = {
        'name': fields.related('address_id', 'partner_id', type='many2one',\
                     relation='res.partner', string='Partner', help="You may\
                     enter Address first,Partner will be linked automatically if any."),
        'address_id': fields.many2one('res.partner.address', 'Address', \
                        help='Address which is linked to the Partner'), # TO Correct: domain=[('partner_id', '=', name)]
        'contact_id': fields.many2one('res.partner.contact','Contact', required=True, ondelete='cascade'),
        'function': fields.char('Partner Function', size=64, help="Function of this contact with this partner"),
        'sequence_contact': fields.integer('Contact Seq.',help='Order of\
                     importance of this address in the list of addresses of the linked contact'),
        'sequence_partner': fields.integer('Partner Seq.',help='Order of importance\
                 of this job title in the list of job title of the linked partner'),
        'email': fields.char('E-Mail', size=240, help="Job E-Mail"),
        'phone': fields.char('Phone', size=64, help="Job Phone no."),
        'fax': fields.char('Fax', size=64, help="Job FAX no."),
        'extension': fields.char('Extension', size=64, help='Internal/External extension phone number'),
        'other': fields.char('Other', size=64, help='Additional phone field'),
        'date_start': fields.date('Date Start',help="Start date of job(Joining Date)"),
        'date_stop': fields.date('Date Stop', help="Last date of job"),
        'state': fields.selection([('past', 'Past'),('current', 'Current')], \
                                'State', required=True, help="Status of Address"),
    }

    _defaults = {
        'sequence_contact' : lambda *a: 0,
        'state': lambda *a: 'current',
    }

    def onchange_name(self, cr, uid, ids, partner_id='', address_id='', context=None):
        address_id = False
        if partner_id:
            partner = self.pool.get('res.partner').browse(cr, uid, partner_id, context=context)
            addresses = [a.id for a in partner.address if a.type == 'contact'] or [a.id for a in partner.address]
            address_id = addresses and addresses[0] or False

        domain = partner_id and [('partner_id', '=', partner_id)] or []

        return {'value': {'address_id': address_id}, 'domain': {'address_id': domain}}

    def onchange_address(self, cr, uid, _, name, address_id, context=None):
        """
            @@param self: The object pointer
            @param cr: the current row, from the database cursor,
            @param uid: the current user,
            @param _: List of IDs,
            @address_id : ID of the Address selected,
            @param context: A standard dictionary for contextual values
        """
        partner_id = False
        if address_id:
            address = self.pool.get('res.partner.address').browse(cr, uid, address_id, context=context)
            partner_id = address.partner_id.id

        domain = name and [('partner_id', '=', name)] or []

        return {'value': {'name': partner_id}, 'domain': {'address_id': domain}}

res_partner_job()


# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:

