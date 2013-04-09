# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2004-2009 Tiny SPRL (<http://tiny.be>).
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

import datetime
from lxml import etree
import pytz
import re

import openerp
from openerp import tools
from openerp.osv import osv, fields
from openerp.osv.scope import proxy as scope
from openerp.osv.api import model, record, recordset, returns
from openerp.tools.translate import _

ADDRESS_FORMAT_LAYOUTS = {
    '%(city)s %(state_code)s\n%(zip)s': """
        <div class="address_format">
            <field name="city" placeholder="City" style="width: 50%%"/>
            <field name="state_id" class="oe_no_button" placeholder="State" style="width: 47%%" options='{"no_open": true}'/>
            <br/>
            <field name="zip" placeholder="ZIP"/>
        </div>
    """,
    '%(zip)s %(city)s': """
        <div class="address_format">
            <field name="zip" placeholder="ZIP" style="width: 40%%"/>
            <field name="city" placeholder="City" style="width: 57%%"/>
            <br/>
            <field name="state_id" class="oe_no_button" placeholder="State" options='{"no_open": true}'/>
        </div>
    """,
    '%(city)s\n%(state_name)s\n%(zip)s': """
        <div class="address_format">
            <field name="city" placeholder="City"/>
            <field name="state_id" class="oe_no_button" placeholder="State" options='{"no_open": true}'/>
            <field name="zip" placeholder="ZIP"/>
        </div>
    """
}


class format_address(object):
    @model
    def fields_view_get_address(self, arch):
        fmt = scope.user.company_id.country_id.address_format or ''
        for k, v in ADDRESS_FORMAT_LAYOUTS.items():
            if k in fmt:
                doc = etree.fromstring(arch)
                for node in doc.xpath("//div[@class='address_format']"):
                    tree = etree.fromstring(v)
                    node.getparent().replace(node, tree)
                arch = etree.tostring(doc)
                break
        return arch


class res_partner_category(osv.Model):

    def name_get(self, cr, uid, ids, context=None):
        """ Return the categories' display name, including their direct
            parent by default.

            If ``context['partner_category_display']`` is ``'short'``, the short
            version of the category name (without the direct parent) is used.
            The default is the long version.
        """
        if not isinstance(ids, list):
            ids = [ids]
        if context is None:
            context = {}

        if context.get('partner_category_display') == 'short':
            return super(res_partner_category, self).name_get(cr, uid, ids, context=context)

        res = []
        for record in self.browse(cr, uid, ids, context):
            id = record.id
            names = []
            while record:
                names.append(record.name)
                record = record.parent_id
            res.append((id, ' / '.join(reversed(names))))
        return res

    @model
    def name_search(self, name, args=None, operator='ilike', limit=100):
        args = args or []
        if name:
            name = name.split(' / ')[-1]
            args = [('name', operator, name)] + args
        categories = self.search(args, limit=limit)
        return categories.name_get()

    @recordset
    def _name_get_fnc(self, field_name, arg):
        return dict(self.name_get())

    _description = 'Partner Categories'
    _name = 'res.partner.category'
    _columns = {
        'name': fields.char('Category Name', required=True, size=64, translate=True),
        'parent_id': fields.many2one('res.partner.category', 'Parent Category', select=True, ondelete='cascade'),
        'complete_name': fields.function(_name_get_fnc, type="char", string='Full Name'),
        'child_ids': fields.one2many('res.partner.category', 'parent_id', 'Child Categories'),
        'active': fields.boolean('Active', help="The active field allows you to hide the category without removing it."),
        'parent_left': fields.integer('Left parent', select=True),
        'parent_right': fields.integer('Right parent', select=True),
        'partner_ids': fields.many2many('res.partner', id1='category_id', id2='partner_id', string='Partners'),
    }
    _constraints = [
        (osv.osv._check_recursion, 'Error ! You can not create recursive categories.', ['parent_id'])
    ]
    _defaults = {
        'active': 1,
    }
    _parent_store = True
    _parent_order = 'name'
    _order = 'parent_left'


class res_partner_title(osv.osv):
    _name = 'res.partner.title'
    _order = 'name'
    _columns = {
        'name': fields.char('Title', required=True, size=46, translate=True),
        'shortcut': fields.char('Abbreviation', size=16, translate=True),
        'domain': fields.selection([('partner', 'Partner'), ('contact', 'Contact')], 'Domain', required=True, size=24)
    }
    _defaults = {
        'domain': 'contact',
    }


@model
def _lang_get(self):
    languages = scope.model('res.lang').search([])
    return [(language.code, language.name) for language in languages]


@model
def _tz_get(self):
    return [(x, x) for x in pytz.all_timezones]

POSTAL_ADDRESS_FIELDS = ('street', 'street2', 'zip', 'city', 'state_id', 'country_id')
ADDRESS_FIELDS = POSTAL_ADDRESS_FIELDS + ('email', 'phone', 'fax', 'mobile', 'website', 'ref', 'lang')


class res_partner(osv.Model, format_address):
    _description = 'Partner'
    _name = "res.partner"

    @recordset
    def _address_display(self, name, arg):
        return dict((p.id, p._display_address()) for p in self)

    @recordset
    def _get_tz_offset(self, name, args):
        return dict(
            (p.id, datetime.datetime.now(pytz.timezone(p.tz or 'GMT')).strftime('%z'))
            for p in self)

    @recordset
    def _get_image(self, name, args):
        return dict((p.id, tools.image_get_resized_images(p.image)) for p in self)

    @record
    def _set_image(self, name, value, args):
        return self.write({'image': tools.image_resize_image_big(value)})

    @recordset
    def _has_image(self, name, args):
        return dict((p.id, bool(p.image)) for p in self)

    _order = "name"
    _columns = {
        'name': fields.char('Name', size=128, required=True, select=True),
        'date': fields.date('Date', select=1),
        'title': fields.many2one('res.partner.title', 'Title'),
        'parent_id': fields.many2one('res.partner', 'Related Company'),
        'child_ids': fields.one2many('res.partner', 'parent_id', 'Contacts'),
        'ref': fields.char('Reference', size=64, select=1),
        'lang': fields.selection(_lang_get, 'Language',
            help="If the selected language is loaded in the system, all documents related to this contact will be printed in this language. If not, it will be English."),
        'tz': fields.selection(_tz_get,  'Timezone', size=64,
            help="The partner's timezone, used to output proper date and time values inside printed reports. "
                 "It is important to set a value for this field. You should use the same timezone "
                 "that is otherwise used to pick and render date and time values: your computer's timezone."),
        'tz_offset': fields.function(_get_tz_offset, type='char', size=5, string='Timezone offset', invisible=True),
        'user_id': fields.many2one('res.users', 'Salesperson', help='The internal user that is in charge of communicating with this contact if any.'),
        'vat': fields.char('TIN', size=32, help="Tax Identification Number. Check the box if this contact is subjected to taxes. Used by the some of the legal statements."),
        'bank_ids': fields.one2many('res.partner.bank', 'partner_id', 'Banks'),
        'website': fields.char('Website', size=64, help="Website of Partner or Company"),
        'comment': fields.text('Notes'),
        'category_id': fields.many2many('res.partner.category', id1='partner_id', id2='category_id', string='Tags'),
        'credit_limit': fields.float(string='Credit Limit'),
        'ean13': fields.char('EAN13', size=13),
        'active': fields.boolean('Active'),
        'customer': fields.boolean('Customer', help="Check this box if this contact is a customer."),
        'supplier': fields.boolean('Supplier', help="Check this box if this contact is a supplier. If it's not checked, purchase people will not see it when encoding a purchase order."),
        'employee': fields.boolean('Employee', help="Check this box if this contact is an Employee."),
        'function': fields.char('Job Position', size=128),
        'type': fields.selection([('default', 'Default'), ('invoice', 'Invoice'),
                                   ('delivery', 'Shipping'), ('contact', 'Contact'),
                                   ('other', 'Other')], 'Address Type',
            help="Used to select automatically the right address according to the context in sales and purchases documents."),
        'street': fields.char('Street', size=128),
        'street2': fields.char('Street2', size=128),
        'zip': fields.char('Zip', change_default=True, size=24),
        'city': fields.char('City', size=128),
        'state_id': fields.many2one("res.country.state", 'State'),
        'country_id': fields.many2one('res.country', 'Country'),
        'country': fields.related('country_id', type='many2one', relation='res.country', string='Country',
                                  deprecated="This field will be removed as of OpenERP 7.1, use country_id instead"),
        'email': fields.char('Email', size=240),
        'phone': fields.char('Phone', size=64),
        'fax': fields.char('Fax', size=64),
        'mobile': fields.char('Mobile', size=64),
        'birthdate': fields.char('Birthdate', size=64),
        'is_company': fields.boolean('Is a Company', help="Check if the contact is a company, otherwise it is a person"),
        'use_parent_address': fields.boolean('Use Company Address', help="Select this if you want to set company's address information  for this contact"),
        # image: all image fields are base64 encoded and PIL-supported
        'image': fields.binary("Image",
            help="This field holds the image used as avatar for this contact, limited to 1024x1024px"),
        'image_medium': fields.function(_get_image, fnct_inv=_set_image,
            string="Medium-sized image", type="binary", multi="_get_image",
            store={
                'res.partner': (lambda self, cr, uid, ids, c={}: ids, ['image'], 10),
            },
            help="Medium-sized image of this contact. It is automatically "\
                 "resized as a 128x128px image, with aspect ratio preserved. "\
                 "Use this field in form views or some kanban views."),
        'image_small': fields.function(_get_image, fnct_inv=_set_image,
            string="Small-sized image", type="binary", multi="_get_image",
            store={
                'res.partner': (lambda self, cr, uid, ids, c={}: ids, ['image'], 10),
            },
            help="Small-sized image of this contact. It is automatically "\
                 "resized as a 64x64px image, with aspect ratio preserved. "\
                 "Use this field anywhere a small image is required."),
        'has_image': fields.function(_has_image, type="boolean"),
        'company_id': fields.many2one('res.company', 'Company', select=1),
        'color': fields.integer('Color Index'),
        'user_ids': fields.one2many('res.users', 'partner_id', 'Users'),
        'contact_address': fields.function(_address_display,  type='char', string='Complete Address'),
    }

    @model
    def _default_category(self):
        category_id = scope.context.get('category_id', False)
        return [category_id] if category_id else False

    @model
    def _get_default_image(self, is_company, colorize=False):
        img_path = openerp.modules.get_module_resource(
            'base', 'static/src/img', 'company_image.png' if is_company else 'avatar.png')
        with open(img_path, 'rb') as f:
            image = f.read()

        # colorize user avatars
        if not is_company:
            image = tools.image_colorize(image)

        return tools.image_resize_image_big(image.encode('base64'))

    @model
    def fields_view_get(self, view_id=None, view_type='form', toolbar=False, submenu=False):
        if (not view_id) and (view_type == 'form') and scope.context.get('force_email'):
            view_id = scope.model('ir.model.data').get_object_reference('base', 'view_partner_simple_form')[1]
        res = super(res_partner, self).fields_view_get(view_id, view_type, toolbar=toolbar, submenu=submenu)
        if view_type == 'form':
            res['arch'] = self.fields_view_get_address(res['arch'])
        return res

    @model
    def _default_company(self):
        return scope.model('res.company')._company_default_get('res.partner')

    _defaults = {
        'active': True,
        'lang': model(lambda self: scope.lang),
        'tz': model(lambda self: scope.context.get('tz', False)),
        'customer': True,
        'category_id': _default_category,
        'company_id': _default_company,
        'color': 0,
        'is_company': False,
        'type': 'default',
        'use_parent_address': True,
        'image': False,
    }

    @record
    def copy(self, default=None):
        default = dict(default or {}, name=_('%s (copy)') % self.name)
        return super(res_partner, self).copy(default)

    @recordset
    def onchange_type(self, is_company):
        value = {}
        value['title'] = False
        if is_company:
            value['parent_id'] = False
            domain = {'title': [('domain', '=', 'partner')]}
        else:
            domain = {'title': [('domain', '=', 'contact')]}
        return {'value': value, 'domain': domain}

    @recordset
    def onchange_address(self, use_parent_address, parent_id):
        def value_or_id(val):
            """ return val or val.id if val is a browse record """
            return val.id if isinstance(val, osv.Record) else val

        if use_parent_address and parent_id:
            parent = self.browse(parent_id)
            return {'value': dict((key, value_or_id(parent[key])) for key in ADDRESS_FIELDS)}
        return {}

    @recordset
    def onchange_state(self, state_id):
        if state_id:
            state = scope.model('res.country.state').browse(state_id)
            return {'value': {'country_id': state.country_id.id}}
        return {}

    @recordset
    def _check_ean_key(self):
        for partner in self:
            value = partner.ean13
            if value:
                if len(value) != 13:
                    return False
                res = sum(int(digit) * weight for digit, weight in zip(value, [1, 3] * 7))
                if res % 10:
                    return False
        return True

#   _constraints = [(_check_ean_key, 'Error: Invalid ean code', ['ean13'])]

    @recordset
    def write(self, vals):
        # Update parent and siblings or children records
        for partner in self:
            others = None
            if partner.is_company:
                domain_children = [('parent_id', 'child_of', partner.id), ('use_parent_address', '=', True)]
                others = self.search(domain_children)
            elif partner.parent_id and vals.get('use_parent_address', partner.use_parent_address):
                domain_siblings = [('parent_id', '=', partner.parent_id.id), ('use_parent_address', '=', True)]
                others = partner.parent_id + self.search(domain_siblings)
            if others:
                others.update_address(vals)
        return super(res_partner, self).write(vals)

    @model
    def create(self, vals):
        if vals.get('parent_id') and vals.get('use_parent_address'):
            # Update parent and siblings records
            parent = self.browse(vals['parent_id'])
            siblings = self.search([('parent_id', '=', parent.id), ('use_parent_address', '=', True)])
            (parent + siblings).update_address(vals)
        return super(res_partner, self).create(vals)

    @recordset
    def update_address(self, vals):
        addr_vals = dict((key, vals[key]) for key in POSTAL_ADDRESS_FIELDS if vals.get(key))
        if addr_vals:
            return super(res_partner, self).write(addr_vals)

    def name_get(self, cr, uid, ids, context=None):
        if not isinstance(ids, list):
            ids = [ids]

        res = []
        for record in self.browse(cr, uid, ids, context):
            name = record.name
            # import pudb; pudb.set_trace()
            if record.parent_id:
                name = "%s (%s)" % (name, record.parent_id.name)
            if scope.context.get('show_address'):
                name = name + "\n" + record._display_address(without_company=True)
                name = "\n".join(filter(bool, name.splitlines()))
            if scope.context.get('show_email') and record.email:
                name = "%s <%s>" % (name, record.email)
            res.append((record.id, name))
        return res

    def _parse_partner_name(self, text, context=None):
        """ Supported syntax:
            - 'Raoul <raoul@grosbedon.fr>': will find name and email address
            - otherwise: default, everything is set as the name
        """
        match = re.search(r'([^\s,<@]+@[^>\s,]+)', text)
        if match:
            email = match.group(1)
            name = text[:text.index(email)].replace('"','').replace('<','').strip()
        else:
            name, email = text, ''
        return name, email

    @model
    def name_create(self, name):
        """ Override of orm's name_create method for partners. The purpose is
            to handle some basic formats to create partners using the
            name_create.
            If only an email address is received and that the regex cannot find
            a name, the name will have the email value.
            If 'force_email' key in context: must find the email address.
        """
        name, email = self._parse_partner_name(name)
        if scope.context.get('force_email') and not email:
            raise osv.except_osv(_('Warning'), _("Couldn't create contact without email address !"))
        if not name and email:
            name = email
        partner = self.create({self._rec_name: name or email, 'email': email or False})
        return partner.recordset().name_get()[0]

    @model
    def name_search(self, name, args=None, operator='ilike', limit=100):
        cr, uid, context = scope
        if not args:
            args = []
        if name and operator in ('=', 'ilike', '=ilike', 'like', '=like'):
            # search on the name of the contacts and of its company
            search_name = name
            if operator in ('ilike', 'like'):
                search_name = '%%%s%%' % name
            if operator in ('=ilike', '=like'):
                operator = operator[1:]
            query_args = {'name': search_name}
            limit_str = ''
            if limit:
                limit_str = ' limit %(limit)s'
                query_args['limit'] = limit
            cr.execute('''SELECT partner.id FROM res_partner partner
                          LEFT JOIN res_partner company ON partner.parent_id = company.id
                          WHERE partner.email ''' + operator +''' %(name)s
                             OR partner.name || ' (' || COALESCE(company.name,'') || ')'
                          ''' + operator + ' %(name)s ' + limit_str, query_args)
            ids = map(lambda x: x[0], cr.fetchall())
            if args:
                partners = self.search([('id', 'in', ids)] + args, limit=limit)
            else:
                partners = self.browse(ids)
            if partners:
                return partners.name_get()

        return super(res_partner, self).name_search(name, args, operator=operator, limit=limit)

    @model
    @returns('self')
    def find_or_create(self, email):
        """ Find a partner with the given ``email`` or use :py:method:`~.name_create`
            to create one

            :param str email: email-like string, which should contain at least one email,
                e.g. ``"Raoul Grosbedon <r.g@grosbedon.fr>"``
        """
        assert email, 'an email is required for find_or_create to work'
        emails = tools.email_split(email)
        if emails:
            email = emails[0]
        partners = self.search([('email', 'ilike', email)])
        if partners:
            return partners[0]
        return self.browse(self.name_create(email)[0])

    @recordset
    def _email_send(self, email_from, subject, body, on_error=None):
        for partner in self:
            if partner.email:
                tools.email_send(email_from, [partner.email], subject, body, on_error)
        return True

    @recordset
    def email_send(self, email_from, subject, body, on_error=''):
        Cron = scope.model('ir.cron')
        ids = map(int, self)
        while len(ids):
            Cron.create({
                'name': 'Send Partner Emails',
                'user_id': scope.uid,
                'model': 'res.partner',
                'function': '_email_send',
                'args': repr([ids[:16], email_from, subject, body, on_error])
            })
            ids = ids[16:]
        return True

    @recordset
    def address_get(self, adr_pref=None):
        if adr_pref is None:
            adr_pref = ['default']

        # retrieve addresses by type from the partner itself and its children
        address_id = {}
        for partner in self:
            address_id[partner.type] = address_id.get(partner.type) or partner.id
            for child in partner.child_ids:
                address_id[child.type] = address_id.get(child.type) or child.id

        # get the default address (if there is one) or the first available address
        default_id = address_id.get('default', self[0].id)
        res = {}
        for addr_type in adr_pref:
            res[addr_type] = address_id.get(addr_type, default_id)
        return res

    @model
    def view_header_get(self, view_id, view_type):
        res = super(res_partner, self).view_header_get(view_id, view_type)
        if res:
            return res
        category_id = scope.context.get('category_id', False)
        category = scope.model('res.partner.category').browse(category_id)
        return _('Partners: ') + category.name if category else False

    @model
    @returns('self')
    def main_partner(self):
        ''' Return the main partner '''
        return scope.ref('base.main_partner')

    @record
    def _display_address(self, without_company=False):
        '''
        The purpose of this function is to build and return an address formatted accordingly to the
        standards of the country where it belongs.

        :returns: the address formatted in a display that fit its country habits (or the default ones
            if not country is specified)
        :rtype: string
        '''

        # get the information that will be injected into the display format
        # get the address format
        address_format = self.country_id.address_format or \
              "%(street)s\n%(street2)s\n%(city)s %(state_code)s %(zip)s\n%(country_name)s"
        args = {
            'state_code': self.state_id.code or '',
            'state_name': self.state_id.name or '',
            'country_code': self.country_id.code or '',
            'country_name': self.country_id.name or '',
            'company_name': self.parent_id.name or '',
        }
        address_field = ['title', 'street', 'street2', 'zip', 'city']
        for field in address_field:
            args[field] = self[field] or ''
        if without_company:
            args['company_name'] = ''
        elif self.parent_id:
            address_format = '%(company_name)s\n' + address_format
        return address_format % args

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
