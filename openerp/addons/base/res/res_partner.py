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

import math
import os
from osv import osv, fields
import re
import tools
from tools.translate import _
import logging
import pooler

class res_payterm(osv.osv):
    _description = 'Payment term'
    _name = 'res.payterm'
    _order = 'name'
    _columns = {
        'name': fields.char('Payment Term (short name)', size=64),
    }

class res_partner_category(osv.osv):

    def name_get(self, cr, uid, ids, context=None):
        """Return the categories' display name, including their direct
           parent by default.

        :param dict context: the ``partner_category_display`` key can be
                             used to select the short version of the
                             category name (without the direct parent),
                             when set to ``'short'``. The default is
                             the long version."""
        if context is None:
            context = {}
        if context.get('partner_category_display') == 'short':
            return super(res_partner_category, self).name_get(cr, uid, ids, context=context)
        if isinstance(ids, (int, long)):
            ids = [ids]
        reads = self.read(cr, uid, ids, ['name','parent_id'], context=context)
        res = []
        for record in reads:
            name = record['name']
            if record['parent_id']:
                name = record['parent_id'][1]+' / '+name
            res.append((record['id'], name))
        return res

    def name_search(self, cr, uid, name, args=None, operator='ilike', context=None, limit=100):
        if not args:
            args=[]
        if not context:
            context={}
        if name:
            # Be sure name_search is symetric to name_get
            name = name.split(' / ')[-1]
            ids = self.search(cr, uid, [('name', operator, name)] + args, limit=limit, context=context)
        else:
            ids = self.search(cr, uid, args, limit=limit, context=context)
        return self.name_get(cr, uid, ids, context)


    def _name_get_fnc(self, cr, uid, ids, prop, unknow_none, context=None):
        res = self.name_get(cr, uid, ids, context=context)
        return dict(res)

    _description='Partner Categories'
    _name = 'res.partner.category'
    _columns = {
        'name': fields.char('Category Name', required=True, size=64, translate=True),
        'parent_id': fields.many2one('res.partner.category', 'Parent Category', select=True, ondelete='cascade'),
        'complete_name': fields.function(_name_get_fnc, type="char", string='Full Name'),
        'child_ids': fields.one2many('res.partner.category', 'parent_id', 'Child Categories'),
        'active' : fields.boolean('Active', help="The active field allows you to hide the category without removing it."),
        'parent_left' : fields.integer('Left parent', select=True),
        'parent_right' : fields.integer('Right parent', select=True),
        'partner_ids': fields.many2many('res.partner', id1='category_id', id2='partner_id', string='Partners'),
    }
    _constraints = [
        (osv.osv._check_recursion, 'Error ! You can not create recursive categories.', ['parent_id'])
    ]
    _defaults = {
        'active' : lambda *a: 1,
    }
    _parent_store = True
    _parent_order = 'name'
    _order = 'parent_left'

class res_partner_title(osv.osv):
    _name = 'res.partner.title'
    _columns = {
        'name': fields.char('Title', required=True, size=46, translate=True),
        'shortcut': fields.char('Abbreviation', required=True, size=16, translate=True),
        'domain': fields.selection([('partner','Partner'),('contact','Contact')], 'Domain', required=True, size=24)
    }
    _order = 'name'

def _lang_get(self, cr, uid, context=None):
    lang_pool = self.pool.get('res.lang')
    ids = lang_pool.search(cr, uid, [], context=context)
    res = lang_pool.read(cr, uid, ids, ['code', 'name'], context)
    return [(r['code'], r['name']) for r in res] + [('','')]

POSTAL_ADDRESS_FIELDS = ('street', 'street2', 'zip', 'city', 'state_id', 'country_id')
ADDRESS_FIELDS = POSTAL_ADDRESS_FIELDS + ('email', 'phone', 'fax', 'mobile', 'website', 'ref', 'lang')

class res_partner(osv.osv):
    _description='Partner'
    _name = "res.partner"

    def _address_display(self, cr, uid, ids, name, args, context=None):
        res={}
        for partner in self.browse(cr, uid, ids, context=context):
            res[partner.id] =self._display_address(cr, uid, partner, context=context)
        return res

    _order = "name"
    _columns = {
        'name': fields.char('Name', size=128, required=True, select=True),
        'date': fields.date('Date', select=1),
        'title': fields.many2one('res.partner.title','Title'),
        'parent_id': fields.many2one('res.partner','Company'),
        'child_ids': fields.one2many('res.partner', 'parent_id', 'Contacts'),
        'ref': fields.char('Reference', size=64, select=1),
        'lang': fields.selection(_lang_get, 'Language', help="If the selected language is loaded in the system, all documents related to this partner will be printed in this language. If not, it will be english."),
        'user_id': fields.many2one('res.users', 'Salesperson', help='The internal user that is in charge of communicating with this partner if any.'),
        'vat': fields.char('VAT',size=32 ,help="Value Added Tax number. Check the box if the partner is subjected to the VAT. Used by the VAT legal statement."),
        'bank_ids': fields.one2many('res.partner.bank', 'partner_id', 'Banks'),
        'website': fields.char('Website',size=64, help="Website of Partner or Company"),
        'comment': fields.text('Notes'),
        'address': fields.one2many('res.partner.address', 'partner_id', 'Contacts'),   # should be removed in version 7, but kept until then for backward compatibility
        'category_id': fields.many2many('res.partner.category', id1='partner_id', id2='category_id', string='Tags'),
        'credit_limit': fields.float(string='Credit Limit'),
        'ean13': fields.char('EAN13', size=13),
        'active': fields.boolean('Active'),
        'customer': fields.boolean('Customer', help="Check this box if the partner is a customer."),
        'supplier': fields.boolean('Supplier', help="Check this box if the partner is a supplier. If it's not checked, purchase people will not see it when encoding a purchase order."),
        'employee': fields.boolean('Employee', help="Check this box if the partner is an Employee."),
        'function': fields.char('Job Position', size=128),
        'type': fields.selection( [('default','Default'),('invoice','Invoice'),
                                   ('delivery','Delivery'), ('contact','Contact'),
                                   ('other','Other')],
                   'Address Type', help="Used to select automatically the right address according to the context in sales and purchases documents."),
        'street': fields.char('Street', size=128),
        'street2': fields.char('Street2', size=128),
        'zip': fields.char('Zip', change_default=True, size=24),
        'city': fields.char('City', size=128),
        'state_id': fields.many2one("res.country.state", 'State', domain="[('country_id','=',country_id)]"),
        'country_id': fields.many2one('res.country', 'Country'),
        'country': fields.related('country_id', type='many2one', relation='res.country', string='Country'),   # for backward compatibility
        'email': fields.char('Email', size=240),
        'phone': fields.char('Phone', size=64),
        'fax': fields.char('Fax', size=64),
        'mobile': fields.char('Mobile', size=64),
        'birthdate': fields.char('Birthdate', size=64),
        'is_company': fields.boolean('Company', help="Check if the contact is a company, otherwise it is a person"),
        'use_parent_address': fields.boolean('Use Company Address', help="Select this if you want to set company's address information  for this contact"),
        'photo': fields.binary('Photo'),
        'company_id': fields.many2one('res.company', 'Company', select=1),
        'color': fields.integer('Color Index'),
        'contact_address': fields.function(_address_display,  type='char', string='Complete Address'),
    }

    def _default_category(self, cr, uid, context=None):
        if context is None:
            context = {}
        if context.get('category_id'):
            return [context['category_id']]
        return False

    def _get_photo(self, cr, uid, is_company, context=None):
        if is_company:
            path = os.path.join( tools.config['root_path'], 'addons', 'base', 'res', 'company_icon.png')
        else:
            path = os.path.join( tools.config['root_path'], 'addons', 'base', 'res', 'photo.png')
        return open(path, 'rb').read().encode('base64')

    _defaults = {
        'active': True,
        'customer': True,
        'category_id': _default_category,
        'company_id': lambda s,cr,uid,c: s.pool.get('res.company')._company_default_get(cr, uid, 'res.partner', context=c),
        'color': 0,
        'is_company': False,
        'type': 'default',
        'use_parent_address': True,
        'photo': lambda self, cr, uid, context: self._get_photo(cr, uid, False, context),
    }

    def copy(self, cr, uid, id, default=None, context=None):
        if default is None:
            default = {}
        name = self.read(cr, uid, [id], ['name'], context)[0]['name']
        default.update({'name': _('%s (copy)')%(name)})
        return super(res_partner, self).copy(cr, uid, id, default, context)

    def onchange_type(self, cr, uid, ids, is_company, context=None):
        value = {'title': False,
                 'photo': self._get_photo(cr, uid, is_company, context)}
        if is_company:
            value['parent_id'] = False
            domain = {'title': [('domain', '=', 'partner')]}
        else:
            domain = {'title': [('domain', '=', 'contact')]}
        return {'value': value, 'domain': domain}

    def onchange_address(self, cr, uid, ids, use_parent_address, parent_id, context=None):
        def value_or_id(val):
            """ return val or val.id if val is a browse record """
            return val if isinstance(val, (bool, int, long, float, basestring)) else val.id

        if use_parent_address and parent_id:
            parent = self.browse(cr, uid, parent_id, context=context)
            return {'value': dict((key, value_or_id(parent[key])) for key in ADDRESS_FIELDS)}
        return {}

    def _check_ean_key(self, cr, uid, ids, context=None):
        for partner_o in pooler.get_pool(cr.dbname).get('res.partner').read(cr, uid, ids, ['ean13',]):
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

    def write(self, cr, uid, ids, vals, context=None):
        # Update parent and siblings or children records
        if isinstance(ids, (int, long)):
            ids = [ids]
        if vals.get('is_company')==False:
            vals.update({'child_ids' : [(5,)]})
        for partner in self.browse(cr, uid, ids, context=context):
            update_ids = []
            if partner.is_company:
                domain_children = [('parent_id', '=', partner.id), ('use_parent_address', '=', True)]
                update_ids = self.search(cr, uid, domain_children, context=context)
            elif partner.parent_id:
                 if vals.get('use_parent_address')==True:
                     domain_siblings = [('parent_id', '=', partner.parent_id.id), ('use_parent_address', '=', True)]
                     update_ids = [partner.parent_id.id] + self.search(cr, uid, domain_siblings, context=context)
                 if 'use_parent_address' not in vals and  partner.use_parent_address:
                    domain_siblings = [('parent_id', '=', partner.parent_id.id), ('use_parent_address', '=', True)]
                    update_ids = [partner.parent_id.id] + self.search(cr, uid, domain_siblings, context=context)
            self.update_address(cr, uid, update_ids, vals, context)
        return super(res_partner,self).write(cr, uid, ids, vals, context=context)

    def create(self, cr, uid, vals, context=None):
        if context is None:
            context={}
        # Update parent and siblings records
        if vals.get('parent_id') and vals.get('use_parent_address'):
            domain_siblings = [('parent_id', '=', vals['parent_id']), ('use_parent_address', '=', True)]
            update_ids = [vals['parent_id']] + self.search(cr, uid, domain_siblings, context=context)
            self.update_address(cr, uid, update_ids, vals, context)
        if 'photo' not in vals  :
            vals['photo'] = self._get_photo(cr, uid, vals.get('is_company', False) or context.get('default_is_company'), context)
        return super(res_partner,self).create(cr, uid, vals, context=context)

    def update_address(self, cr, uid, ids, vals, context=None):
        addr_vals = dict((key, vals[key]) for key in POSTAL_ADDRESS_FIELDS if vals.get(key))
        return super(res_partner, self).write(cr, uid, ids, addr_vals, context)

    def name_get(self, cr, uid, ids, context=None):
        if context is None:
            context = {}
        if isinstance(ids, (int, long)):
            ids = [ids]
        res = []
        for record in self.browse(cr, uid, ids, context=context):
            name = record.name
            if record.parent_id:
                name =  "%s (%s)" % (name, record.parent_id.name)
            if context.get('show_address'):
                name = name + "\n" + self._display_address(cr, uid, record, without_company=True, context=context)
                name = name.replace('\n\n','\n')
                name = name.replace('\n\n','\n')
            res.append((record.id, name))
        return res

    def name_create(self, cr, uid, name, context=None):
        """ Override of orm's name_create method for partners. The purpose is
            to handle some basic formats to create partners using the
            name_create.
            Supported syntax:
            - 'raoul@grosbedon.fr': create a partner with name raoul@grosbedon.fr
              and sets its email to raoul@grosbedon.fr
            - 'Raoul Grosbedon <raoul@grosbedon.fr>': create a partner with name
              Raoul Grosbedon, and set its email to raoul@grosbedon.fr
            - anything else: fall back on the default name_create
            Regex :
            - ([a-zA-Z0-9._%-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,4}): raoul@grosbedon.fr
            - ([\w\s.\\-]+)[\<]([a-zA-Z0-9._%-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,4})[\>]:
              Raoul Grosbedon, raoul@grosbedon.fr
        """
        contact_regex = re.compile('([\w\s.\\-]+)[\<]([a-zA-Z0-9._%-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,4})[\>]')
        email_regex = re.compile('([a-zA-Z0-9._%-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,4})')
        contact_regex_res = contact_regex.findall(name)
        email_regex_res = email_regex.findall(name)
        if contact_regex_res:
            name = contact_regex_res[0][0].rstrip(' ') # remove extra spaces on the right
            email = contact_regex_res[0][1]
            rec_id = self.create(cr, uid, {self._rec_name: name, 'email': email}, context);
            return self.name_get(cr, uid, [rec_id], context)[0]
        elif email_regex:
            email = '%s' % (email_regex_res[0])
            rec_id = self.create(cr, uid, {self._rec_name: email, 'email': email}, context);
            return self.name_get(cr, uid, [rec_id], context)[0]
        else:
            return super(res_partner, self).create(cr, uid, name, context)

    def name_search(self, cr, uid, name, args=None, operator='ilike', context=None, limit=100):
        if not args:
            args = []
        if name and operator in ('=', 'ilike', '=ilike', 'like'):
            # search on the name of the contacts and of its company
            name2 = operator == '=' and name or '%' + name + '%'
            limit_str = ''
            query_args = [name2]
            if limit:
                limit_str = ' limit %s'
                query_args += [limit]
            cr.execute('''SELECT partner.id FROM res_partner partner
                          LEFT JOIN res_partner company ON partner.parent_id = company.id
                          WHERE partner.name || ' (' || COALESCE(company.name,'') || ')'
                          ''' + operator + ''' %s ''' + limit_str, query_args)
            ids = map(lambda x: x[0], cr.fetchall())
            if args:
                ids = self.search(cr, uid, [('id', 'in', ids)] + args, limit=limit, context=context)
            if ids:
                return self.name_get(cr, uid, ids, context)
        return super(res_partner,self).name_search(cr, uid, name, args, operator=operator, context=context, limit=limit)

    def _email_send(self, cr, uid, ids, email_from, subject, body, on_error=None):
        partners = self.browse(cr, uid, ids)
        for partner in partners:
            if partner.email:
                tools.email_send(email_from, [partner.email], subject, body, on_error)
        return True

    def email_send(self, cr, uid, ids, email_from, subject, body, on_error=''):
        while len(ids):
            self.pool.get('ir.cron').create(cr, uid, {
                'name': 'Send Partner Emails',
                'user_id': uid,
                'model': 'res.partner',
                'function': '_email_send',
                'args': repr([ids[:16], email_from, subject, body, on_error])
            })
            ids = ids[16:]
        return True

    def address_get(self, cr, uid, ids, adr_pref=None):
        if adr_pref is None:
            adr_pref = ['default']
        result = {}
        # retrieve addresses from the partner itself and its children
        res = []
        # need to fix the ids ,It get False value in list like ids[False]
        if ids and ids[0]!=False:
            for p in self.browse(cr, uid, ids):
                res.append((p.type, p.id))
                res.extend((c.type, c.id) for c in p.child_ids)
        address_dict = dict(reversed(res))
        # get the id of the (first) default address if there is one,
        # otherwise get the id of the first address in the list
        default_address = False
        if res:
            default_address = address_dict.get('default', res[0][1])
        for adr in adr_pref:
            result[adr] = address_dict.get(adr, default_address)
        return result

    def gen_next_ref(self, cr, uid, ids):
        if len(ids) != 1:
            return True

        # compute the next number ref
        cr.execute("select ref from res_partner where ref is not null order by char_length(ref) desc, ref desc limit 1")
        res = cr.dictfetchall()
        ref = res and res[0]['ref'] or '0'
        try:
            nextref = int(ref)+1
        except:
            raise osv.except_osv(_('Warning'), _("Couldn't generate the next id because some partners have an alphabetic id !"))

        # update the current partner
        cr.execute("update res_partner set ref=%s where id=%s", (nextref, ids[0]))
        return True

    def view_header_get(self, cr, uid, view_id, view_type, context):
        res = super(res_partner, self).view_header_get(cr, uid, view_id, view_type, context)
        if res: return res
        if (not context.get('category_id', False)):
            return False
        return _('Partners: ')+self.pool.get('res.partner.category').browse(cr, uid, context['category_id'], context).name

    def main_partner(self, cr, uid):
        ''' Return the id of the main partner
        '''
        model_data = self.pool.get('ir.model.data')
        return model_data.browse(cr, uid,
                            model_data.search(cr, uid, [('module','=','base'),
                                                ('name','=','main_partner')])[0],
                ).res_id

    def _display_address(self, cr, uid, address, without_company=False, context=None):

        '''
        The purpose of this function is to build and return an address formatted accordingly to the
        standards of the country where it belongs.

        :param address: browse record of the res.partner.address to format
        :returns: the address formatted in a display that fit its country habits (or the default ones
            if not country is specified)
        :rtype: string
        '''

        # get the information that will be injected into the display format
        # get the address format
        address_format = address.country_id and address.country_id.address_format or \
                                         '%(company_name)s\n%(street)s\n%(street2)s\n%(city)s,%(state_code)s %(zip)s'
        args = {
            'state_code': address.state_id and address.state_id.code or '',
            'state_name': address.state_id and address.state_id.name or '',
            'country_code': address.country_id and address.country_id.code or '',
            'country_name': address.country_id and address.country_id.name or '',
            'company_name': address.parent_id and address.parent_id.name or '',
        }
        address_field = ['title', 'street', 'street2', 'zip', 'city']
        for field in address_field :
            args[field] = getattr(address, field) or ''
        if without_company:
            args['company_name'] = ''
        return address_format % args



# res.partner.address is deprecated; it is still there for backward compability only and will be removed in next version
class res_partner_address(osv.osv):
    _table = "res_partner"
    _name = 'res.partner.address'
    _order = 'type, name'
    _columns = {
        'parent_id': fields.many2one('res.partner', 'Company', ondelete='set null', select=True),
        'partner_id': fields.related('parent_id', type='many2one', relation='res.partner', string='Partner'),   # for backward compatibility
        'type': fields.selection( [ ('default','Default'),('invoice','Invoice'), ('delivery','Delivery'), ('contact','Contact'), ('other','Other') ],'Address Type', help="Used to select automatically the right address according to the context in sales and purchases documents."),
        'function': fields.char('Function', size=128),
        'title': fields.many2one('res.partner.title','Title'),
        'name': fields.char('Contact Name', size=64, select=1),
        'street': fields.char('Street', size=128),
        'street2': fields.char('Street2', size=128),
        'zip': fields.char('Zip', change_default=True, size=24),
        'city': fields.char('City', size=128),
        'state_id': fields.many2one("res.country.state", 'Fed. State', domain="[('country_id','=',country_id)]"),
        'country_id': fields.many2one('res.country', 'Country'),
        'email': fields.char('Email', size=240),
        'phone': fields.char('Phone', size=64),
        'fax': fields.char('Fax', size=64),
        'mobile': fields.char('Mobile', size=64),
        'birthdate': fields.char('Birthdate', size=64),
        'is_customer_add': fields.related('partner_id', 'customer', type='boolean', string='Customer'),
        'is_supplier_add': fields.related('partner_id', 'supplier', type='boolean', string='Supplier'),
        'active': fields.boolean('Active', help="Uncheck the active field to hide the contact."),
        'company_id': fields.many2one('res.company', 'Company',select=1),
        'color': fields.integer('Color Index'),
    }

    _defaults = {
        'active': True,
        'company_id': lambda s,cr,uid,c: s.pool.get('res.company')._company_default_get(cr, uid, 'res.partner', context=c),
        'color': 0,
        'type': 'default',
    }

    def write(self, cr, uid, ids, vals, context=None):
        logging.getLogger('res.partner').warning("Deprecated use of res.partner.address")
        if 'partner_id' in vals:
            vals['parent_id'] = vals.get('partner_id')
            del(vals['partner_id'])
        return self.pool.get('res.partner').write(cr, uid, ids, vals, context=context)

    def create(self, cr, uid, vals, context=None):
        logging.getLogger('res.partner').warning("Deprecated use of res.partner.address")
        if 'partner_id' in vals:
            vals['parent_id'] = vals.get('partner_id')
            del(vals['partner_id'])
        return self.pool.get('res.partner').create(cr, uid, vals, context=context)

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
