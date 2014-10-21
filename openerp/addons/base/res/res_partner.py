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
import math
import pytz
import urlparse

import openerp
from openerp import tools, api
from openerp.osv import osv, fields
from openerp.osv.expression import get_unaccent_wrapper
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
    @api.model
    def fields_view_get_address(self, arch):
        fmt = self.env.user.company_id.country_id.address_format or ''
        for k, v in ADDRESS_FORMAT_LAYOUTS.items():
            if k in fmt:
                doc = etree.fromstring(arch)
                for node in doc.xpath("//div[@class='address_format']"):
                    tree = etree.fromstring(v)
                    node.getparent().replace(node, tree)
                arch = etree.tostring(doc)
                break
        return arch


@api.model
def _tz_get(self):
    # put POSIX 'Etc/*' entries at the end to avoid confusing users - see bug 1086728
    return [(tz,tz) for tz in sorted(pytz.all_timezones, key=lambda tz: tz if not tz.startswith('Etc/') else '_')]


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
        for category in self.browse(cr, uid, ids, context=context):
            names = []
            current = category
            while current:
                names.append(current.name)
                current = current.parent_id
            res.append((category.id, ' / '.join(reversed(names))))
        return res

    @api.model
    def name_search(self, name, args=None, operator='ilike', limit=100):
        args = args or []
        if name:
            # Be sure name_search is symetric to name_get
            name = name.split(' / ')[-1]
            args = [('name', operator, name)] + args
        categories = self.search(args, limit=limit)
        return categories.name_get()

    @api.multi
    def _name_get_fnc(self, field_name, arg):
        return dict(self.name_get())

    _description = 'Partner Tags'
    _name = 'res.partner.category'
    _columns = {
        'name': fields.char('Category Name', required=True, translate=True),
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
        'name': fields.char('Title', required=True, translate=True),
        'shortcut': fields.char('Abbreviation', translate=True),
        'domain': fields.selection([('partner', 'Partner'), ('contact', 'Contact')], 'Domain', required=True)
    }
    _defaults = {
        'domain': 'contact',
    }


@api.model
def _lang_get(self):
    languages = self.env['res.lang'].search([])
    return [(language.code, language.name) for language in languages]

# fields copy if 'use_parent_address' is checked
ADDRESS_FIELDS = ('street', 'street2', 'zip', 'city', 'state_id', 'country_id')


class res_partner(osv.Model, format_address):
    _description = 'Partner'
    _name = "res.partner"

    def _address_display(self, cr, uid, ids, name, args, context=None):
        res = {}
        for partner in self.browse(cr, uid, ids, context=context):
            res[partner.id] = self._display_address(cr, uid, partner, context=context)
        return res

    @api.multi
    def _get_tz_offset(self, name, args):
        return dict(
            (p.id, datetime.datetime.now(pytz.timezone(p.tz or 'GMT')).strftime('%z'))
            for p in self)

    @api.multi
    def _get_image(self, name, args):
        return dict((p.id, tools.image_get_resized_images(p.image)) for p in self)

    @api.one
    def _set_image(self, name, value, args):
        return self.write({'image': tools.image_resize_image_big(value)})

    @api.multi
    def _has_image(self, name, args):
        return dict((p.id, bool(p.image)) for p in self)

    def _commercial_partner_compute(self, cr, uid, ids, name, args, context=None):
        """ Returns the partner that is considered the commercial
        entity of this partner. The commercial entity holds the master data
        for all commercial fields (see :py:meth:`~_commercial_fields`) """
        result = dict.fromkeys(ids, False)
        for partner in self.browse(cr, uid, ids, context=context):
            current_partner = partner 
            while not current_partner.is_company and current_partner.parent_id:
                current_partner = current_partner.parent_id
            result[partner.id] = current_partner.id
        return result

    def _display_name_compute(self, cr, uid, ids, name, args, context=None):
        context = dict(context or {})
        context.pop('show_address', None)
        context.pop('show_address_only', None)
        context.pop('show_email', None)
        return dict(self.name_get(cr, uid, ids, context=context))

    # indirections to avoid passing a copy of the overridable method when declaring the function field
    _commercial_partner_id = lambda self, *args, **kwargs: self._commercial_partner_compute(*args, **kwargs)
    _display_name = lambda self, *args, **kwargs: self._display_name_compute(*args, **kwargs)

    _commercial_partner_store_triggers = {
        'res.partner': (lambda self,cr,uid,ids,context=None: self.search(cr, uid, [('id','child_of',ids)], context=dict(active_test=False)),
                        ['parent_id', 'is_company'], 10)
    }
    _display_name_store_triggers = {
        'res.partner': (lambda self,cr,uid,ids,context=None: self.search(cr, uid, [('id','child_of',ids)], context=dict(active_test=False)),
                        ['parent_id', 'is_company', 'name'], 10)
    }

    _order = "display_name"
    _columns = {
        'name': fields.char('Name', required=True, select=True),
        'display_name': fields.function(_display_name, type='char', string='Name', store=_display_name_store_triggers, select=True),
        'date': fields.date('Date', select=1),
        'title': fields.many2one('res.partner.title', 'Title'),
        'parent_id': fields.many2one('res.partner', 'Related Company', select=True),
        'parent_name': fields.related('parent_id', 'name', type='char', readonly=True, string='Parent name'),
        'child_ids': fields.one2many('res.partner', 'parent_id', 'Contacts', domain=[('active','=',True)]), # force "active_test" domain to bypass _search() override
        'ref': fields.char('Internal Reference', select=1),
        'lang': fields.selection(_lang_get, 'Language',
            help="If the selected language is loaded in the system, all documents related to this contact will be printed in this language. If not, it will be English."),
        'tz': fields.selection(_tz_get,  'Timezone', size=64,
            help="The partner's timezone, used to output proper date and time values inside printed reports. "
                 "It is important to set a value for this field. You should use the same timezone "
                 "that is otherwise used to pick and render date and time values: your computer's timezone."),
        'tz_offset': fields.function(_get_tz_offset, type='char', size=5, string='Timezone offset', invisible=True),
        'user_id': fields.many2one('res.users', 'Salesperson', help='The internal user that is in charge of communicating with this contact if any.'),
        'vat': fields.char('TIN', help="Tax Identification Number. Check the box if this contact is subjected to taxes. Used by the some of the legal statements."),
        'bank_ids': fields.one2many('res.partner.bank', 'partner_id', 'Banks'),
        'website': fields.char('Website', help="Website of Partner or Company"),
        'comment': fields.text('Notes'),
        'category_id': fields.many2many('res.partner.category', id1='partner_id', id2='category_id', string='Tags'),
        'credit_limit': fields.float(string='Credit Limit'),
        'ean13': fields.char('EAN13', size=13),
        'active': fields.boolean('Active'),
        'customer': fields.boolean('Is a Customer', help="Check this box if this contact is a customer."),
        'supplier': fields.boolean('Is a Supplier', help="Check this box if this contact is a supplier. If it's not checked, purchase people will not see it when encoding a purchase order."),
        'employee': fields.boolean('Employee', help="Check this box if this contact is an Employee."),
        'function': fields.char('Job Position'),
        'type': fields.selection([('default', 'Default'), ('invoice', 'Invoice'),
                                   ('delivery', 'Shipping'), ('contact', 'Contact'),
                                   ('other', 'Other')], 'Address Type',
            help="Used to select automatically the right address according to the context in sales and purchases documents."),
        'street': fields.char('Street'),
        'street2': fields.char('Street2'),
        'zip': fields.char('Zip', size=24, change_default=True),
        'city': fields.char('City'),
        'state_id': fields.many2one("res.country.state", 'State', ondelete='restrict'),
        'country_id': fields.many2one('res.country', 'Country', ondelete='restrict'),
        'email': fields.char('Email'),
        'phone': fields.char('Phone'),
        'fax': fields.char('Fax'),
        'mobile': fields.char('Mobile'),
        'birthdate': fields.char('Birthdate'),
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

        # technical field used for managing commercial fields
        'commercial_partner_id': fields.function(_commercial_partner_id, type='many2one', relation='res.partner', string='Commercial Entity', store=_commercial_partner_store_triggers)
    }

    @api.model
    def _default_category(self):
        category_id = self.env.context.get('category_id', False)
        return [category_id] if category_id else False

    @api.model
    def _get_default_image(self, is_company, colorize=False):
        img_path = openerp.modules.get_module_resource(
            'base', 'static/src/img', 'company_image.png' if is_company else 'avatar.png')
        with open(img_path, 'rb') as f:
            image = f.read()

        # colorize user avatars
        if not is_company:
            image = tools.image_colorize(image)

        return tools.image_resize_image_big(image.encode('base64'))

    def fields_view_get(self, cr, user, view_id=None, view_type='form', context=None, toolbar=False, submenu=False):
        if (not view_id) and (view_type=='form') and context and context.get('force_email', False):
            view_id = self.pool['ir.model.data'].get_object_reference(cr, user, 'base', 'view_partner_simple_form')[1]
        res = super(res_partner,self).fields_view_get(cr, user, view_id, view_type, context, toolbar=toolbar, submenu=submenu)
        if view_type == 'form':
            res['arch'] = self.fields_view_get_address(cr, user, res['arch'], context=context)
        return res

    @api.model
    def _default_company(self):
        return self.env['res.company']._company_default_get('res.partner')

    _defaults = {
        'active': True,
        'lang': api.model(lambda self: self.env.lang),
        'tz': api.model(lambda self: self.env.context.get('tz', False)),
        'customer': True,
        'category_id': _default_category,
        'company_id': _default_company,
        'color': 0,
        'is_company': False,
        'type': 'contact', # type 'default' is wildcard and thus inappropriate
        'use_parent_address': False,
        'image': False,
    }

    _constraints = [
        (osv.osv._check_recursion, 'You cannot create recursive Partner hierarchies.', ['parent_id']),
    ]

    @api.one
    def copy(self, default=None):
        default = dict(default or {})
        default['name'] = _('%s (copy)') % self.name
        return super(res_partner, self).copy(default)

    @api.multi
    def onchange_type(self, is_company):
        value = {'title': False}
        if is_company:
            value['use_parent_address'] = False
            domain = {'title': [('domain', '=', 'partner')]}
        else:
            domain = {'title': [('domain', '=', 'contact')]}
        return {'value': value, 'domain': domain}

    def onchange_address(self, cr, uid, ids, use_parent_address, parent_id, context=None):
        def value_or_id(val):
            """ return val or val.id if val is a browse record """
            return val if isinstance(val, (bool, int, long, float, basestring)) else val.id
        result = {}
        if parent_id:
            if ids:
                partner = self.browse(cr, uid, ids[0], context=context)
                if partner.parent_id and partner.parent_id.id != parent_id:
                    result['warning'] = {'title': _('Warning'),
                                         'message': _('Changing the company of a contact should only be done if it '
                                                      'was never correctly set. If an existing contact starts working for a new '
                                                      'company then a new contact should be created under that new '
                                                      'company. You can use the "Discard" button to abandon this change.')}
            if use_parent_address:
                parent = self.browse(cr, uid, parent_id, context=context)
                address_fields = self._address_fields(cr, uid, context=context)
                result['value'] = dict((key, value_or_id(parent[key])) for key in address_fields)
        else:
            result['value'] = {'use_parent_address': False}
        return result

    @api.multi
    def onchange_state(self, state_id):
        if state_id:
            state = self.env['res.country.state'].browse(state_id)
            return {'value': {'country_id': state.country_id.id}}
        return {}

    def _check_ean_key(self, cr, uid, ids, context=None):
        for partner_o in self.pool['res.partner'].read(cr, uid, ids, ['ean13',]):
            thisean=partner_o['ean13']
            if thisean and thisean!='':
                if len(thisean)!=13:
                    return False
                sum=0
                for i in range(12):
                    if not (i % 2):
                        sum+=int(thisean[i])
                    else:
                        sum+=3*int(thisean[i])
                if math.ceil(sum/10.0)*10-sum!=int(thisean[12]):
                    return False
        return True

#   _constraints = [(_check_ean_key, 'Error: Invalid ean code', ['ean13'])]

    def _update_fields_values(self, cr, uid, partner, fields, context=None):
        """ Returns dict of write() values for synchronizing ``fields`` """
        values = {}
        for field in fields:
            column = self._all_columns[field].column
            if column._type == 'one2many':
                raise AssertionError('One2Many fields cannot be synchronized as part of `commercial_fields` or `address fields`')
            if column._type == 'many2one':
                values[field] = partner[field].id if partner[field] else False
            elif column._type == 'many2many':
                values[field] = [(6,0,[r.id for r in partner[field] or []])]
            else:
                values[field] = partner[field]
        return values

    def _address_fields(self, cr, uid, context=None):
        """ Returns the list of address fields that are synced from the parent
        when the `use_parent_address` flag is set. """
        return list(ADDRESS_FIELDS)

    def update_address(self, cr, uid, ids, vals, context=None):
        address_fields = self._address_fields(cr, uid, context=context)
        addr_vals = dict((key, vals[key]) for key in address_fields if key in vals)
        if addr_vals:
            return super(res_partner, self).write(cr, uid, ids, addr_vals, context)

    def _commercial_fields(self, cr, uid, context=None):
        """ Returns the list of fields that are managed by the commercial entity
        to which a partner belongs. These fields are meant to be hidden on
        partners that aren't `commercial entities` themselves, and will be
        delegated to the parent `commercial entity`. The list is meant to be
        extended by inheriting classes. """
        return ['vat']

    def _commercial_sync_from_company(self, cr, uid, partner, context=None):
        """ Handle sync of commercial fields when a new parent commercial entity is set,
        as if they were related fields """
        commercial_partner = partner.commercial_partner_id
        if not commercial_partner:
            # On child partner creation of a parent partner,
            # the commercial_partner_id is not yet computed
            commercial_partner_id = self._commercial_partner_compute(
                cr, uid, [partner.id], 'commercial_partner_id', [], context=context)[partner.id]
            commercial_partner = self.browse(cr, uid, commercial_partner_id, context=context)
        if commercial_partner != partner:
            commercial_fields = self._commercial_fields(cr, uid, context=context)
            sync_vals = self._update_fields_values(cr, uid, commercial_partner,
                                                   commercial_fields, context=context)
            partner.write(sync_vals)

    def _commercial_sync_to_children(self, cr, uid, partner, context=None):
        """ Handle sync of commercial fields to descendants """
        commercial_fields = self._commercial_fields(cr, uid, context=context)
        commercial_partner = partner.commercial_partner_id
        if not commercial_partner:
            # On child partner creation of a parent partner,
            # the commercial_partner_id is not yet computed
            commercial_partner_id = self._commercial_partner_compute(
                cr, uid, [partner.id], 'commercial_partner_id', [], context=context)[partner.id]
            commercial_partner = self.browse(cr, uid, commercial_partner_id, context=context)
        sync_vals = self._update_fields_values(cr, uid, commercial_partner,
                                               commercial_fields, context=context)
        sync_children = [c for c in partner.child_ids if not c.is_company]
        for child in sync_children:
            self._commercial_sync_to_children(cr, uid, child, context=context)
        return self.write(cr, uid, [c.id for c in sync_children], sync_vals, context=context)

    def _fields_sync(self, cr, uid, partner, update_values, context=None):
        """ Sync commercial fields and address fields from company and to children after create/update,
        just as if those were all modeled as fields.related to the parent """
        # 1. From UPSTREAM: sync from parent
        if update_values.get('parent_id') or update_values.get('use_parent_address'):
            # 1a. Commercial fields: sync if parent changed
            if update_values.get('parent_id'):
                self._commercial_sync_from_company(cr, uid, partner, context=context)
            # 1b. Address fields: sync if parent or use_parent changed *and* both are now set 
            if partner.parent_id and partner.use_parent_address:
                onchange_vals = self.onchange_address(cr, uid, [partner.id],
                                                      use_parent_address=partner.use_parent_address,
                                                      parent_id=partner.parent_id.id,
                                                      context=context).get('value', {})
                partner.update_address(onchange_vals)

        # 2. To DOWNSTREAM: sync children 
        if partner.child_ids:
            # 2a. Commercial Fields: sync if commercial entity
            if partner.commercial_partner_id == partner:
                commercial_fields = self._commercial_fields(cr, uid,
                                                            context=context)
                if any(field in update_values for field in commercial_fields):
                    self._commercial_sync_to_children(cr, uid, partner,
                                                      context=context)
            # 2b. Address fields: sync if address changed
            address_fields = self._address_fields(cr, uid, context=context)
            if any(field in update_values for field in address_fields):
                domain_children = [('parent_id', '=', partner.id), ('use_parent_address', '=', True)]
                update_ids = self.search(cr, uid, domain_children, context=context)
                self.update_address(cr, uid, update_ids, update_values, context=context)

    def _handle_first_contact_creation(self, cr, uid, partner, context=None):
        """ On creation of first contact for a company (or root) that has no address, assume contact address
        was meant to be company address """
        parent = partner.parent_id
        address_fields = self._address_fields(cr, uid, context=context)
        if parent and (parent.is_company or not parent.parent_id) and len(parent.child_ids) == 1 and \
            any(partner[f] for f in address_fields) and not any(parent[f] for f in address_fields):
            addr_vals = self._update_fields_values(cr, uid, partner, address_fields, context=context)
            parent.update_address(addr_vals)
            if not parent.is_company:
                parent.write({'is_company': True})

    def _clean_website(self, website):
        (scheme, netloc, path, params, query, fragment) = urlparse.urlparse(website)
        if not scheme:
            if not netloc:
                netloc, path = path, ''
            website = urlparse.urlunparse(('http', netloc, path, params, query, fragment))
        return website

    @api.multi
    def write(self, vals):
        # res.partner must only allow to set the company_id of a partner if it
        # is the same as the company of all users that inherit from this partner
        # (this is to allow the code from res_users to write to the partner!) or
        # if setting the company_id to False (this is compatible with any user
        # company)
        if vals.get('website'):
            vals['website'] = self._clean_website(vals['website'])
        if vals.get('company_id'):
            company = self.env['res.company'].browse(vals['company_id'])
            for partner in self:
                if partner.user_ids:
                    companies = set(user.company_id for user in partner.user_ids)
                    if len(companies) > 1 or company not in companies:
                        raise osv.except_osv(_("Warning"),_("You can not change the company as the partner/user has multiple user linked with different companies."))

        result = super(res_partner, self).write(vals)
        for partner in self:
            self._fields_sync(partner, vals)
        return result

    @api.model
    def create(self, vals):
        if vals.get('website'):
            vals['website'] = self._clean_website(vals['website'])
        partner = super(res_partner, self).create(vals)
        self._fields_sync(partner, vals)
        self._handle_first_contact_creation(partner)
        return partner

    def open_commercial_entity(self, cr, uid, ids, context=None):
        """ Utility method used to add an "Open Company" button in partner views """
        partner = self.browse(cr, uid, ids[0], context=context)
        return {'type': 'ir.actions.act_window',
                'res_model': 'res.partner',
                'view_mode': 'form',
                'res_id': partner.commercial_partner_id.id,
                'target': 'new',
                'flags': {'form': {'action_buttons': True}}}

    def open_parent(self, cr, uid, ids, context=None):
        """ Utility method used to add an "Open Parent" button in partner views """
        partner = self.browse(cr, uid, ids[0], context=context)
        return {'type': 'ir.actions.act_window',
                'res_model': 'res.partner',
                'view_mode': 'form',
                'res_id': partner.parent_id.id,
                'target': 'new',
                'flags': {'form': {'action_buttons': True}}}

    def name_get(self, cr, uid, ids, context=None):
        if context is None:
            context = {}
        if isinstance(ids, (int, long)):
            ids = [ids]
        res = []
        for record in self.browse(cr, uid, ids, context=context):
            name = record.name
            if record.parent_id and not record.is_company:
                name = "%s, %s" % (record.parent_name, name)
            if context.get('show_address_only'):
                name = self._display_address(cr, uid, record, without_company=True, context=context)
            if context.get('show_address'):
                name = name + "\n" + self._display_address(cr, uid, record, without_company=True, context=context)
            name = name.replace('\n\n','\n')
            name = name.replace('\n\n','\n')
            if context.get('show_email') and record.email:
                name = "%s <%s>" % (name, record.email)
            res.append((record.id, name))
        return res

    def _parse_partner_name(self, text, context=None):
        """ Supported syntax:
            - 'Raoul <raoul@grosbedon.fr>': will find name and email address
            - otherwise: default, everything is set as the name """
        emails = tools.email_split(text.replace(' ',','))
        if emails:
            email = emails[0]
            name = text[:text.index(email)].replace('"', '').replace('<', '').strip()
        else:
            name, email = text, ''
        return name, email

    def name_create(self, cr, uid, name, context=None):
        """ Override of orm's name_create method for partners. The purpose is
            to handle some basic formats to create partners using the
            name_create.
            If only an email address is received and that the regex cannot find
            a name, the name will have the email value.
            If 'force_email' key in context: must find the email address. """
        if context is None:
            context = {}
        name, email = self._parse_partner_name(name, context=context)
        if context.get('force_email') and not email:
            raise osv.except_osv(_('Warning'), _("Couldn't create contact without email address!"))
        if not name and email:
            name = email
        rec_id = self.create(cr, uid, {self._rec_name: name or email, 'email': email or False}, context=context)
        return self.name_get(cr, uid, [rec_id], context)[0]

    def _search(self, cr, user, args, offset=0, limit=None, order=None, context=None, count=False, access_rights_uid=None):
        """ Override search() to always show inactive children when searching via ``child_of`` operator. The ORM will
        always call search() with a simple domain of the form [('parent_id', 'in', [ids])]. """
        # a special ``domain`` is set on the ``child_ids`` o2m to bypass this logic, as it uses similar domain expressions
        if len(args) == 1 and len(args[0]) == 3 and args[0][:2] == ('parent_id','in') \
                and args[0][2] != [False]:
            context = dict(context or {}, active_test=False)
        return super(res_partner, self)._search(cr, user, args, offset=offset, limit=limit, order=order, context=context,
                                                count=count, access_rights_uid=access_rights_uid)

    def name_search(self, cr, uid, name, args=None, operator='ilike', context=None, limit=100):
        if not args:
            args = []
        if name and operator in ('=', 'ilike', '=ilike', 'like', '=like'):

            self.check_access_rights(cr, uid, 'read')
            where_query = self._where_calc(cr, uid, args, context=context)
            self._apply_ir_rules(cr, uid, where_query, 'read', context=context)
            from_clause, where_clause, where_clause_params = where_query.get_sql()
            where_str = where_clause and (" WHERE %s AND " % where_clause) or ' WHERE '

            # search on the name of the contacts and of its company
            search_name = name
            if operator in ('ilike', 'like'):
                search_name = '%%%s%%' % name
            if operator in ('=ilike', '=like'):
                operator = operator[1:]

            unaccent = get_unaccent_wrapper(cr)

            query = """SELECT id
                         FROM res_partner
                      {where} ({email} {operator} {percent}
                           OR {display_name} {operator} {percent})
                     ORDER BY {display_name}
                    """.format(where=where_str, operator=operator,
                               email=unaccent('email'),
                               display_name=unaccent('display_name'),
                               percent=unaccent('%s'))

            where_clause_params += [search_name, search_name]
            if limit:
                query += ' limit %s'
                where_clause_params.append(limit)
            cr.execute(query, where_clause_params)
            ids = map(lambda x: x[0], cr.fetchall())

            if ids:
                return self.name_get(cr, uid, ids, context)
            else:
                return []
        return super(res_partner,self).name_search(cr, uid, name, args, operator=operator, context=context, limit=limit)

    def find_or_create(self, cr, uid, email, context=None):
        """ Find a partner with the given ``email`` or use :py:method:`~.name_create`
            to create one

            :param str email: email-like string, which should contain at least one email,
                e.g. ``"Raoul Grosbedon <r.g@grosbedon.fr>"``"""
        assert email, 'an email is required for find_or_create to work'
        emails = tools.email_split(email)
        if emails:
            email = emails[0]
        ids = self.search(cr, uid, [('email','ilike',email)], context=context)
        if not ids:
            return self.name_create(cr, uid, email, context=context)[0]
        return ids[0]

    def _email_send(self, cr, uid, ids, email_from, subject, body, on_error=None):
        partners = self.browse(cr, uid, ids)
        for partner in partners:
            if partner.email:
                tools.email_send(email_from, [partner.email], subject, body, on_error)
        return True

    def email_send(self, cr, uid, ids, email_from, subject, body, on_error=''):
        while len(ids):
            self.pool['ir.cron'].create(cr, uid, {
                'name': 'Send Partner Emails',
                'user_id': uid,
                'model': 'res.partner',
                'function': '_email_send',
                'args': repr([ids[:16], email_from, subject, body, on_error])
            })
            ids = ids[16:]
        return True

    def address_get(self, cr, uid, ids, adr_pref=None, context=None):
        """ Find contacts/addresses of the right type(s) by doing a depth-first-search
        through descendants within company boundaries (stop at entities flagged ``is_company``)
        then continuing the search at the ancestors that are within the same company boundaries.
        Defaults to partners of type ``'default'`` when the exact type is not found, or to the
        provided partner itself if no type ``'default'`` is found either. """
        adr_pref = set(adr_pref or [])
        if 'default' not in adr_pref:
            adr_pref.add('default')
        result = {}
        visited = set()
        for partner in self.browse(cr, uid, filter(None, ids), context=context):
            current_partner = partner
            while current_partner:
                to_scan = [current_partner]
                # Scan descendants, DFS
                while to_scan:
                    record = to_scan.pop(0)
                    visited.add(record)
                    if record.type in adr_pref and not result.get(record.type):
                        result[record.type] = record.id
                    if len(result) == len(adr_pref):
                        return result
                    to_scan = [c for c in record.child_ids
                                 if c not in visited
                                 if not c.is_company] + to_scan

                # Continue scanning at ancestor if current_partner is not a commercial entity
                if current_partner.is_company or not current_partner.parent_id:
                    break
                current_partner = current_partner.parent_id

        # default to type 'default' or the partner itself
        default = result.get('default', partner.id)
        for adr_type in adr_pref:
            result[adr_type] = result.get(adr_type) or default 
        return result

    def view_header_get(self, cr, uid, view_id, view_type, context):
        res = super(res_partner, self).view_header_get(cr, uid, view_id, view_type, context)
        if res: return res
        if not context.get('category_id', False):
            return False
        return _('Partners: ')+self.pool['res.partner.category'].browse(cr, uid, context['category_id'], context).name

    @api.model
    @api.returns('self')
    def main_partner(self):
        ''' Return the main partner '''
        return self.env.ref('base.main_partner')

    def _display_address(self, cr, uid, address, without_company=False, context=None):

        '''
        The purpose of this function is to build and return an address formatted accordingly to the
        standards of the country where it belongs.

        :param address: browse record of the res.partner to format
        :returns: the address formatted in a display that fit its country habits (or the default ones
            if not country is specified)
        :rtype: string
        '''

        # get the information that will be injected into the display format
        # get the address format
        address_format = address.country_id.address_format or \
              "%(street)s\n%(street2)s\n%(city)s %(state_code)s %(zip)s\n%(country_name)s"
        args = {
            'state_code': address.state_id.code or '',
            'state_name': address.state_id.name or '',
            'country_code': address.country_id.code or '',
            'country_name': address.country_id.name or '',
            'company_name': address.parent_name or '',
        }
        for field in self._address_fields(cr, uid, context=context):
            args[field] = getattr(address, field) or ''
        if without_company:
            args['company_name'] = ''
        elif address.parent_id:
            address_format = '%(company_name)s\n' + address_format
        return address_format % args

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
