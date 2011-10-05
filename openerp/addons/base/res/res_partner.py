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

from osv import fields,osv
import tools
import pooler
from tools.translate import _

class res_payterm(osv.osv):
    _description = 'Payment term'
    _name = 'res.payterm'
    _order = 'name'
    _columns = {
        'name': fields.char('Payment Term (short name)', size=64),
    }
res_payterm()

class res_partner_category(osv.osv):
    def name_get(self, cr, uid, ids, context=None):
        if not len(ids):
            return []
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
        'complete_name': fields.function(_name_get_fnc, method=True, type="char", string='Full Name'),
        'child_ids': fields.one2many('res.partner.category', 'parent_id', 'Child Categories'),
        'active' : fields.boolean('Active', help="The active field allows you to hide the category without removing it."),
        'parent_left' : fields.integer('Left parent', select=True),
        'parent_right' : fields.integer('Right parent', select=True),
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
res_partner_category()

class res_partner_title(osv.osv):
    _name = 'res.partner.title'
    _columns = {
        'name': fields.char('Title', required=True, size=46, translate=True),
        'shortcut': fields.char('Shortcut', required=True, size=16, translate=True),
        'domain': fields.selection([('partner','Partner'),('contact','Contact')], 'Domain', required=True, size=24)
    }
    _order = 'name'
res_partner_title()

def _lang_get(self, cr, uid, context={}):
    obj = self.pool.get('res.lang')
    ids = obj.search(cr, uid, [], context=context)
    res = obj.read(cr, uid, ids, ['code', 'name'], context)
    return [(r['code'], r['name']) for r in res] + [('','')]


class res_partner(osv.osv):
    _description='Partner'
    _name = "res.partner"
    _order = "name"
    _columns = {
        'name': fields.char('Name', size=128, required=True, select=True),
        'date': fields.date('Date', select=1),
        'title': fields.many2one('res.partner.title','Partner Firm'),
        'parent_id': fields.many2one('res.partner','Parent Partner'),
        'child_ids': fields.one2many('res.partner', 'parent_id', 'Partner Ref.'),
        'ref': fields.char('Reference', size=64, select=1),
        'lang': fields.selection(_lang_get, 'Language', help="If the selected language is loaded in the system, all documents related to this partner will be printed in this language. If not, it will be english."),
        'user_id': fields.many2one('res.users', 'Salesman', help='The internal user that is in charge of communicating with this partner if any.'),
        'vat': fields.char('VAT',size=32 ,help="Value Added Tax number. Check the box if the partner is subjected to the VAT. Used by the VAT legal statement."),
        'bank_ids': fields.one2many('res.partner.bank', 'partner_id', 'Banks'),
        'website': fields.char('Website',size=64, help="Website of Partner."),
        'comment': fields.text('Notes'),
        'address': fields.one2many('res.partner.address', 'partner_id', 'Contacts'),
        'category_id': fields.many2many('res.partner.category', 'res_partner_category_rel', 'partner_id', 'category_id', 'Categories'),
        'events': fields.one2many('res.partner.event', 'partner_id', 'Events'),
        'credit_limit': fields.float(string='Credit Limit'),
        'ean13': fields.char('EAN13', size=13),
        'active': fields.boolean('Active'),
        'customer': fields.boolean('Customer', help="Check this box if the partner is a customer."),
        'supplier': fields.boolean('Supplier', help="Check this box if the partner is a supplier. If it's not checked, purchase people will not see it when encoding a purchase order."),
        'city': fields.related('address', 'city', type='char', string='City'),
        'function': fields.related('address', 'function', type='char', string='function'),
        'subname': fields.related('address', 'name', type='char', string='Contact Name'),
        'phone': fields.related('address', 'phone', type='char', string='Phone'),
        'mobile': fields.related('address', 'mobile', type='char', string='Mobile'),
        'country': fields.related('address', 'country_id', type='many2one', relation='res.country', string='Country'),
        'employee': fields.boolean('Employee', help="Check this box if the partner is an Employee."),
        'email': fields.related('address', 'email', type='char', size=240, string='E-mail'),
        'company_id': fields.many2one('res.company', 'Company', select=1),
        'color': fields.integer('Color Index'),
    }

    def _default_category(self, cr, uid, context={}):
        if 'category_id' in context and context['category_id']:
            return [context['category_id']]
        return []

    _defaults = {
        'active': lambda *a: 1,
        'customer': lambda *a: 1,
        'address': [{'type': 'default'}],
        'category_id': _default_category,
        'company_id': lambda s,cr,uid,c: s.pool.get('res.company')._company_default_get(cr, uid, 'res.partner', context=c),
        'color': 0,
    }

    def copy(self, cr, uid, id, default={}, context={}):
        name = self.read(cr, uid, [id], ['name'])[0]['name']
        default.update({'name': name+ _(' (copy)'), 'events':[]})
        return super(res_partner, self).copy(cr, uid, id, default, context)

    def do_share(self, cr, uid, ids, *args):
        return True

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

    def name_get(self, cr, uid, ids, context={}):
        if not len(ids):
            return []
        if context and context.get('show_ref'):
            rec_name = 'ref'
        else:
            rec_name = 'name'

        res = [(r['id'], r[rec_name]) for r in self.read(cr, uid, ids, [rec_name], context)]
        return res

    def name_search(self, cr, uid, name, args=None, operator='ilike', context=None, limit=100):
        if not args:
            args=[]
        if name:
            ids = self.search(cr, uid, [('ref', '=', name)] + args, limit=limit, context=context)
            if not ids:
                ids = self.search(cr, uid, [('name', operator, name)] + args, limit=limit, context=context)
        else:
            ids = self.search(cr, uid, args, limit=limit, context=context)
        return self.name_get(cr, uid, ids, context)

    def _email_send(self, cr, uid, ids, email_from, subject, body, on_error=None):
        partners = self.browse(cr, uid, ids)
        for partner in partners:
            if len(partner.address):
                if partner.address[0].email:
                    tools.email_send(email_from, [partner.address[0].email], subject, body, on_error)
        return True

    def email_send(self, cr, uid, ids, email_from, subject, body, on_error=''):
        while len(ids):
            self.pool.get('ir.cron').create(cr, uid, {
                'name': 'Send Partner Emails',
                'user_id': uid,
#               'nextcall': False,
                'model': 'res.partner',
                'function': '_email_send',
                'args': repr([ids[:16], email_from, subject, body, on_error])
            })
            ids = ids[16:]
        return True

    def address_get(self, cr, uid, ids, adr_pref=['default']):
        address_obj = self.pool.get('res.partner.address')
        address_ids = address_obj.search(cr, uid, [('partner_id', '=', ids)])
        address_rec = address_obj.read(cr, uid, address_ids, ['type'])
        res = list(tuple(addr.values()) for addr in address_rec)
        adr = dict(res)
        # get the id of the (first) default address if there is one,
        # otherwise get the id of the first address in the list
        if res:
            default_address = adr.get('default', res[0][1])
        else:
            default_address = False
        result = {}
        for a in adr_pref:
            result[a] = adr.get(a, default_address)
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
        return model_data.browse(
            cr, uid,
            model_data.search(cr, uid, [('module','=','base'),
                                        ('name','=','main_partner')])[0],
            ).res_id
res_partner()

class res_partner_address(osv.osv):
    _description ='Partner Addresses'
    _name = 'res.partner.address'
    _order = 'type, name'
    _columns = {
        'partner_id': fields.many2one('res.partner', 'Partner Name', ondelete='set null', select=True, help="Keep empty for a private address, not related to partner."),
        'type': fields.selection( [ ('default','Default'),('invoice','Invoice'), ('delivery','Delivery'), ('contact','Contact'), ('other','Other') ],'Address Type', help="Used to select automatically the right address according to the context in sales and purchases documents."),
        'function': fields.char('Function', size=64),
        'title': fields.many2one('res.partner.title','Title'),
        'name': fields.char('Contact Name', size=64, select=1),
        'street': fields.char('Street', size=128),
        'street2': fields.char('Street2', size=128),
        'zip': fields.char('Zip', change_default=True, size=24),
        'city': fields.char('City', size=128),
        'state_id': fields.many2one("res.country.state", 'Fed. State', domain="[('country_id','=',country_id)]"),
        'country_id': fields.many2one('res.country', 'Country'),
        'email': fields.char('E-Mail', size=240),
        'phone': fields.char('Phone', size=64),
        'fax': fields.char('Fax', size=64),
        'mobile': fields.char('Mobile', size=64),
        'birthdate': fields.char('Birthdate', size=64),
        'is_customer_add': fields.related('partner_id', 'customer', type='boolean', string='Customer'),
        'is_supplier_add': fields.related('partner_id', 'supplier', type='boolean', string='Supplier'),
        'active': fields.boolean('Active', help="Uncheck the active field to hide the contact."),
#        'company_id': fields.related('partner_id','company_id',type='many2one',relation='res.company',string='Company', store=True),
        'company_id': fields.many2one('res.company', 'Company',select=1),
        'color': fields.integer('Color Index'),
    }
    _defaults = {
        'active': lambda *a: 1,
        'company_id': lambda s,cr,uid,c: s.pool.get('res.company')._company_default_get(cr, uid, 'res.partner.address', context=c),
    }

    def name_get(self, cr, user, ids, context={}):
        if context is None:
            context = {}
        if not len(ids):
            return []
        res = []
        for r in self.read(cr, user, ids, ['name','zip','country_id', 'city','partner_id', 'street']):
            if context.get('contact_display', 'contact')=='partner' and r['partner_id']:
                res.append((r['id'], r['partner_id'][1]))
            else:
                # make a comma-separated list with the following non-empty elements
                elems = [r['name'], r['country_id'] and r['country_id'][1], r['city'], r['street']]
                addr = ', '.join(filter(bool, elems))
                if (context.get('contact_display', 'contact')=='partner_address') and r['partner_id']:
                    res.append((r['id'], "%s: %s" % (r['partner_id'][1], addr or '/')))
                else:
                    res.append((r['id'], addr or '/'))
        return res

    def name_search(self, cr, user, name, args=None, operator='ilike', context=None, limit=100):
        if not args:
            args=[]
        if not context:
            context={}
        if context.get('contact_display', 'contact')=='partner ' or context.get('contact_display', 'contact')=='partner_address '  :
            ids = self.search(cr, user, [('partner_id',operator,name)], limit=limit, context=context)
        else:
            if not name:
                ids = self.search(cr, user, args, limit=limit, context=context)
            else:
                ids = self.search(cr, user, [('zip','=',name)] + args, limit=limit, context=context)
            if not ids:
                ids = self.search(cr, user, [('city',operator,name)] + args, limit=limit, context=context)
            if name:
                ids += self.search(cr, user, [('name',operator,name)] + args, limit=limit, context=context)
                ids += self.search(cr, user, [('partner_id',operator,name)] + args, limit=limit, context=context)
        return self.name_get(cr, user, ids, context=context)

    def get_city(self, cr, uid, id):
        return self.browse(cr, uid, id).city

res_partner_address()

class res_partner_category(osv.osv):
    _inherit = 'res.partner.category'
    _columns = {
        'partner_ids': fields.many2many('res.partner', 'res_partner_category_rel', 'category_id', 'partner_id', 'Partners'),
    }

res_partner_category()

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:

