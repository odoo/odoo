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

import os
import re
import openerp
from openerp import SUPERUSER_ID, tools
from openerp.osv import fields, osv
from openerp.tools.translate import _
from openerp.tools.safe_eval import safe_eval as eval
from openerp.tools import image_resize_image
  
class multi_company_default(osv.osv):
    """
    Manage multi company default value
    """
    _name = 'multi_company.default'
    _description = 'Default multi company'
    _order = 'company_id,sequence,id'

    _columns = {
        'sequence': fields.integer('Sequence'),
        'name': fields.char('Name', required=True, help='Name it to easily find a record'),
        'company_id': fields.many2one('res.company', 'Main Company', required=True,
            help='Company where the user is connected'),
        'company_dest_id': fields.many2one('res.company', 'Default Company', required=True,
            help='Company to store the current record'),
        'object_id': fields.many2one('ir.model', 'Object', required=True,
            help='Object affected by this rule'),
        'expression': fields.char('Expression', required=True,
            help='Expression, must be True to match\nuse context.get or user (browse)'),
        'field_id': fields.many2one('ir.model.fields', 'Field', help='Select field property'),
    }

    _defaults = {
        'expression': 'True',
        'sequence': 100,
    }

    def copy(self, cr, uid, id, default=None, context=None):
        """
        Add (copy) in the name when duplicate record
        """
        if not context:
            context = {}
        if not default:
            default = {}
        company = self.browse(cr, uid, id, context=context)
        default = default.copy()
        default['name'] = company.name + _(' (copy)')
        return super(multi_company_default, self).copy(cr, uid, id, default, context=context)

multi_company_default()

class res_company(osv.osv):
    _name = "res.company"
    _description = 'Companies'
    _order = 'name'
    
    def _get_address_data(self, cr, uid, ids, field_names, arg, context=None):
        """ Read the 'address' functional fields. """
        result = {}
        part_obj = self.pool.get('res.partner')
        for company in self.browse(cr, uid, ids, context=context):
            result[company.id] = {}.fromkeys(field_names, False)
            if company.partner_id:
                address_data = part_obj.address_get(cr, openerp.SUPERUSER_ID, [company.partner_id.id], adr_pref=['default'])
                if address_data['default']:
                    address = part_obj.read(cr, openerp.SUPERUSER_ID, [address_data['default']], field_names, context=context)[0]
                    for field in field_names:
                        result[company.id][field] = address[field] or False
        return result

    def _set_address_data(self, cr, uid, company_id, name, value, arg, context=None):
        """ Write the 'address' functional fields. """
        company = self.browse(cr, uid, company_id, context=context)
        if company.partner_id:
            part_obj = self.pool.get('res.partner')
            address_data = part_obj.address_get(cr, uid, [company.partner_id.id], adr_pref=['default'])
            address = address_data['default']
            if address:
                part_obj.write(cr, uid, [address], {name: value or False}, context=context)
            else:
                part_obj.create(cr, uid, {name: value or False, 'parent_id': company.partner_id.id}, context=context)
        return True

    def _get_logo_web(self, cr, uid, ids, _field_name, _args, context=None):
        result = dict.fromkeys(ids, False)
        for record in self.browse(cr, uid, ids, context=context):
            size = (180, None)
            result[record.id] = image_resize_image(record.partner_id.image, size)
        return result
        
    def _get_companies_from_partner(self, cr, uid, ids, context=None):
        return self.pool['res.company'].search(cr, uid, [('partner_id', 'in', ids)], context=context)

    _columns = {
        'name': fields.related('partner_id', 'name', string='Company Name', size=128, required=True, store=True, type='char'),
        'parent_id': fields.many2one('res.company', 'Parent Company', select=True),
        'child_ids': fields.one2many('res.company', 'parent_id', 'Child Companies'),
        'partner_id': fields.many2one('res.partner', 'Partner', required=True),
        'rml_header': fields.text('RML Header', required=True),
        'rml_header1': fields.char('Company Tagline', help="Appears by default on the top right corner of your printed documents (report header)."),
        'rml_header2': fields.text('RML Internal Header', required=True),
        'rml_header3': fields.text('RML Internal Header for Landscape Reports', required=True),
        'rml_footer': fields.text('Report Footer', help="Footer text displayed at the bottom of all reports."),
        'rml_footer_readonly': fields.related('rml_footer', type='text', string='Report Footer', readonly=True),
        'custom_footer': fields.boolean('Custom Footer', help="Check this to define the report footer manually.  Otherwise it will be filled in automatically."),
        'font': fields.many2one('res.font', string="Font", domain=[('mode', 'in', ('Normal', 'Regular', 'all', 'Book'))],
            help="Set the font into the report header, it will be used as default font in the RML reports of the user company"),
        'logo': fields.related('partner_id', 'image', string="Logo", type="binary"),
        'logo_web': fields.function(_get_logo_web, string="Logo Web", type="binary", store={
            'res.company': (lambda s, c, u, i, x: i, ['partner_id'], 10),
            'res.partner': (_get_companies_from_partner, ['image'], 10),
        }),
        'currency_id': fields.many2one('res.currency', 'Currency', required=True),
        'currency_ids': fields.one2many('res.currency', 'company_id', 'Currency'),
        'user_ids': fields.many2many('res.users', 'res_company_users_rel', 'cid', 'user_id', 'Accepted Users'),
        'account_no':fields.char('Account No.'),
        'street': fields.function(_get_address_data, fnct_inv=_set_address_data, size=128, type='char', string="Street", multi='address'),
        'street2': fields.function(_get_address_data, fnct_inv=_set_address_data, size=128, type='char', string="Street2", multi='address'),
        'zip': fields.function(_get_address_data, fnct_inv=_set_address_data, size=24, type='char', string="Zip", multi='address'),
        'city': fields.function(_get_address_data, fnct_inv=_set_address_data, size=24, type='char', string="City", multi='address'),
        'state_id': fields.function(_get_address_data, fnct_inv=_set_address_data, type='many2one', relation='res.country.state', string="Fed. State", multi='address'),
        'bank_ids': fields.one2many('res.partner.bank','company_id', 'Bank Accounts', help='Bank accounts related to this company'),
        'country_id': fields.function(_get_address_data, fnct_inv=_set_address_data, type='many2one', relation='res.country', string="Country", multi='address'),
        'email': fields.related('partner_id', 'email', size=64, type='char', string="Email", store=True),
        'phone': fields.related('partner_id', 'phone', size=64, type='char', string="Phone", store=True),
        'fax': fields.function(_get_address_data, fnct_inv=_set_address_data, size=64, type='char', string="Fax", multi='address'),
        'website': fields.related('partner_id', 'website', string="Website", type="char", size=64),
        'vat': fields.related('partner_id', 'vat', string="Tax ID", type="char", size=32),
        'company_registry': fields.char('Company Registry', size=64),
        'rml_paper_format': fields.selection([('a4', 'A4'), ('us_letter', 'US Letter')], "Paper Format", required=True, oldname='paper_format'),
    }
    _sql_constraints = [
        ('name_uniq', 'unique (name)', 'The company name must be unique !')
    ]

    def onchange_footer(self, cr, uid, ids, custom_footer, phone, fax, email, website, vat, company_registry, bank_ids, context=None):
        if custom_footer:
            return {}

        # first line (notice that missing elements are filtered out before the join)
        res = ' | '.join(filter(bool, [
            phone            and '%s: %s' % (_('Phone'), phone),
            fax              and '%s: %s' % (_('Fax'), fax),
            email            and '%s: %s' % (_('Email'), email),
            website          and '%s: %s' % (_('Website'), website),
            vat              and '%s: %s' % (_('TIN'), vat),
            company_registry and '%s: %s' % (_('Reg'), company_registry),
        ]))
        # second line: bank accounts
        res_partner_bank = self.pool.get('res.partner.bank')
        account_data = self.resolve_2many_commands(cr, uid, 'bank_ids', bank_ids, context=context)
        account_names = res_partner_bank._prepare_name_get(cr, uid, account_data, context=context)
        if account_names:
            title = _('Bank Accounts') if len(account_names) > 1 else _('Bank Account')
            res += '\n%s: %s' % (title, ', '.join(name for id, name in account_names))

        return {'value': {'rml_footer': res, 'rml_footer_readonly': res}}

    def onchange_state(self, cr, uid, ids, state_id, context=None):
        if state_id:
            return {'value':{'country_id': self.pool.get('res.country.state').browse(cr, uid, state_id, context).country_id.id }}
        return {}
        
    def onchange_font_name(self, cr, uid, ids, font, rml_header, rml_header2, rml_header3, context=None):
        """ To change default header style of all <para> and drawstring. """

        def _change_header(header,font):
            """ Replace default fontname use in header and setfont tag """
            
            default_para = re.sub('fontName.?=.?".*"', 'fontName="%s"'% font, header)
            return re.sub('(<setFont.?name.?=.?)(".*?")(.)', '\g<1>"%s"\g<3>'% font, default_para)
        
        if not font:
            return True
        fontname = self.pool.get('res.font').browse(cr, uid, font, context=context).name
        return {'value':{
                        'rml_header': _change_header(rml_header, fontname),
                        'rml_header2':_change_header(rml_header2, fontname),
                        'rml_header3':_change_header(rml_header3, fontname)
                        }}

    def on_change_country(self, cr, uid, ids, country_id, context=None):
        res = {'domain': {'state_id': []}}
        currency_id = self._get_euro(cr, uid, context=context)
        if country_id:
            currency_id = self.pool.get('res.country').browse(cr, uid, country_id, context=context).currency_id.id
            res['domain'] = {'state_id': [('country_id','=',country_id)]}
        res['value'] = {'currency_id': currency_id}
        return res

    def name_search(self, cr, uid, name='', args=None, operator='ilike', context=None, limit=100):
        context = dict(context or {})
        if context.pop('user_preference', None):
            # We browse as superuser. Otherwise, the user would be able to
            # select only the currently visible companies (according to rules,
            # which are probably to allow to see the child companies) even if
            # she belongs to some other companies.
            user = self.pool.get('res.users').browse(cr, SUPERUSER_ID, uid, context=context)
            cmp_ids = list(set([user.company_id.id] + [cmp.id for cmp in user.company_ids]))
            uid = SUPERUSER_ID
            args = (args or []) + [('id', 'in', cmp_ids)]
        return super(res_company, self).name_search(cr, uid, name=name, args=args, operator=operator, context=context, limit=limit)

    def _company_default_get(self, cr, uid, object=False, field=False, context=None):
        """
        Check if the object for this company have a default value
        """
        if not context:
            context = {}
        proxy = self.pool.get('multi_company.default')
        args = [
            ('object_id.model', '=', object),
            ('field_id', '=', field),
            ('company_id', '=', self.pool['res.users']._get_company(cr, uid, context=context)),
        ]

        ids = proxy.search(cr, uid, args, context=context, order='sequence')
        user = self.pool.get('res.users').browse(cr, SUPERUSER_ID, uid, context=context)
        for rule in proxy.browse(cr, uid, ids, context):
            if eval(rule.expression, {'context': context, 'user': user}):
                return rule.company_dest_id.id
        return user.company_id.id

    @tools.ormcache()
    def _get_company_children(self, cr, uid=None, company=None):
        if not company:
            return []
        ids =  self.search(cr, uid, [('parent_id','child_of',[company])])
        return ids

    def _get_partner_hierarchy(self, cr, uid, company_id, context=None):
        if company_id:
            parent_id = self.browse(cr, uid, company_id)['parent_id']
            if parent_id:
                return self._get_partner_hierarchy(cr, uid, parent_id.id, context)
            else:
                return self._get_partner_descendance(cr, uid, company_id, [], context)
        return []

    def _get_partner_descendance(self, cr, uid, company_id, descendance, context=None):
        descendance.append(self.browse(cr, uid, company_id).partner_id.id)
        for child_id in self._get_company_children(cr, uid, company_id):
            if child_id != company_id:
                descendance = self._get_partner_descendance(cr, uid, child_id, descendance)
        return descendance

    #
    # This function restart the cache on the _get_company_children method
    #
    def cache_restart(self, cr):
        self._get_company_children.clear_cache(self)

    def create(self, cr, uid, vals, context=None):
        if not vals.get('name', False) or vals.get('partner_id', False):
            self.cache_restart(cr)
            return super(res_company, self).create(cr, uid, vals, context=context)
        obj_partner = self.pool.get('res.partner')
        partner_id = obj_partner.create(cr, uid, {'name': vals['name'], 'is_company':True, 'image': vals.get('logo', False)}, context=context)
        vals.update({'partner_id': partner_id})
        self.cache_restart(cr)
        company_id = super(res_company, self).create(cr, uid, vals, context=context)
        obj_partner.write(cr, uid, [partner_id], {'company_id': company_id}, context=context)
        return company_id

    def write(self, cr, uid, ids, values, context=None):
        self.cache_restart(cr)
        return super(res_company, self).write(cr, uid, ids, values, context=context)

    def _get_euro(self, cr, uid, context=None):
        rate_obj = self.pool.get('res.currency.rate')
        rate_id = rate_obj.search(cr, uid, [('rate', '=', 1)], context=context)
        return rate_id and rate_obj.browse(cr, uid, rate_id[0], context=context).currency_id.id or False

    def _get_logo(self, cr, uid, ids):
        return open(os.path.join( tools.config['root_path'], 'addons', 'base', 'res', 'res_company_logo.png'), 'rb') .read().encode('base64')

    def _get_font(self, cr, uid, ids):
        font_obj = self.pool.get('res.font')
        res = font_obj.search(cr, uid, [('family', '=', 'Helvetica'), ('mode', '=', 'all')], limit=1)
        return res and res[0] or False       

    _header = """
<header>
<pageTemplate>
    <frame id="first" x1="28.0" y1="28.0" width="%s" height="%s"/>
    <stylesheet>
       <!-- Set here the default font to use for all <para> tags -->
       <paraStyle name='Normal' fontName="DejaVuSans"/>
    </stylesheet>
    <pageGraphics>
        <fill color="black"/>
        <stroke color="black"/>
        <setFont name="DejaVuSans" size="8"/>
        <drawString x="%s" y="%s"> [[ formatLang(time.strftime("%%Y-%%m-%%d"), date=True) ]]  [[ time.strftime("%%H:%%M") ]]</drawString>
        <setFont name="DejaVuSans-Bold" size="10"/>
        <drawCentredString x="%s" y="%s">[[ company.partner_id.name ]]</drawCentredString>
        <stroke color="#000000"/>
        <lines>%s</lines>
        <!-- Set here the default font to use for all <drawString> tags -->
        <!-- don't forget to change the 2 other occurence of <setFont> above if needed --> 
        <setFont name="DejaVuSans" size="8"/>
    </pageGraphics>
</pageTemplate>
</header>"""

    _header2 = _header % (539, 772, "1.0cm", "28.3cm", "11.1cm", "28.3cm", "1.0cm 28.1cm 20.1cm 28.1cm")

    _header3 = _header % (786, 525, 25, 555, 440, 555, "25 550 818 550")

    def _get_header(self,cr,uid,ids):
        try :
            header_file = tools.file_open(os.path.join('base', 'report', 'corporate_rml_header.rml'))
            try:
                return header_file.read()
            finally:
                header_file.close()
        except:
            return self._header_a4

    _header_main = """
<header>
    <pageTemplate>
        <frame id="first" x1="1.3cm" y1="3.0cm" height="%s" width="19.0cm"/>
         <stylesheet>
            <!-- Set here the default font to use for all <para> tags -->
            <paraStyle name='Normal' fontName="DejaVuSans"/>
            <paraStyle name="main_footer" fontSize="8.0" alignment="CENTER"/>
            <paraStyle name="main_header" fontSize="8.0" leading="10" alignment="LEFT" spaceBefore="0.0" spaceAfter="0.0"/>
         </stylesheet>
        <pageGraphics>
            <!-- Set here the default font to use for all <drawString> tags -->
            <setFont name="DejaVuSans" size="8"/>
            <!-- You Logo - Change X,Y,Width and Height -->
            <image x="1.3cm" y="%s" height="40.0" >[[ company.logo or removeParentNode('image') ]]</image>
            <fill color="black"/>
            <stroke color="black"/>

            <!-- page header -->
            <lines>1.3cm %s 20cm %s</lines>
            <drawRightString x="20cm" y="%s">[[ company.rml_header1 ]]</drawRightString>
            <drawString x="1.3cm" y="%s">[[ company.partner_id.name ]]</drawString>
            <place x="1.3cm" y="%s" height="1.8cm" width="15.0cm">
                <para style="main_header">[[ display_address(company.partner_id) or  '' ]]</para>
            </place>
            <drawString x="1.3cm" y="%s">Phone:</drawString>
            <drawRightString x="7cm" y="%s">[[ company.partner_id.phone or '' ]]</drawRightString>
            <drawString x="1.3cm" y="%s">Mail:</drawString>
            <drawRightString x="7cm" y="%s">[[ company.partner_id.email or '' ]]</drawRightString>
            <lines>1.3cm %s 7cm %s</lines>

            <!-- left margin -->
            <rotate degrees="90"/>
            <fill color="grey"/>
            <drawString x="2.65cm" y="-0.4cm">generated by Odoo.com</drawString>
            <fill color="black"/>
            <rotate degrees="-90"/>

            <!--page bottom-->
            <lines>1.2cm 2.65cm 19.9cm 2.65cm</lines>
            <place x="1.3cm" y="0cm" height="2.55cm" width="19.0cm">
                <para style="main_footer">[[ company.rml_footer ]]</para>
                <para style="main_footer">Contact : [[ user.name ]] - Page: <pageNumber/></para>
            </place>
        </pageGraphics>
    </pageTemplate>
</header>"""

    _header_a4 = _header_main % ('21.7cm', '27.7cm', '27.7cm', '27.7cm', '27.8cm', '27.3cm', '25.3cm', '25.0cm', '25.0cm', '24.6cm', '24.6cm', '24.5cm', '24.5cm')
    _header_letter = _header_main % ('20cm', '26.0cm', '26.0cm', '26.0cm', '26.1cm', '25.6cm', '23.6cm', '23.3cm', '23.3cm', '22.9cm', '22.9cm', '22.8cm', '22.8cm')

    def onchange_rml_paper_format(self, cr, uid, ids, rml_paper_format, context=None):
        if rml_paper_format == 'us_letter':
            return {'value': {'rml_header': self._header_letter}}
        return {'value': {'rml_header': self._header_a4}}

    def act_discover_fonts(self, cr, uid, ids, context=None):
        return self.pool.get("res.font").font_scan(cr, uid, context=context)

    _defaults = {
        'currency_id': _get_euro,
        'rml_paper_format': 'a4',
        'rml_header':_get_header,
        'rml_header2': _header2,
        'rml_header3': _header3,
        'logo':_get_logo,
        'font':_get_font,
    }

    _constraints = [
        (osv.osv._check_recursion, 'Error! You can not create recursive companies.', ['parent_id'])
    ]

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
