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

from osv import osv
from osv import fields
import os
import tools
from tools.translate import _
from tools.safe_eval import safe_eval as eval
from lxml import etree

import pooler
import netsvc
from report.interface import report_rml
from tools import to_xml
from report import report_sxw

class multi_company_default(osv.osv):
    """
    Manage multi company default value
    """
    _name = 'multi_company.default'
    _description = 'Default multi company'
    _order = 'company_id,sequence,id'

    _columns = {
        'sequence': fields.integer('Sequence'),
        'name': fields.char('Name', size=256, required=True, help='Name it to easily find a record'),
        'company_id': fields.many2one('res.company', 'Main Company', required=True,
            help='Company where the user is connected'),
        'company_dest_id': fields.many2one('res.company', 'Default Company', required=True,
            help='Company to store the current record'),
        'object_id': fields.many2one('ir.model', 'Object', required=True,
            help='Object affected by this rule'),
        'expression': fields.char('Expression', size=256, required=True,
            help='Expression, must be True to match\nuse context.get or user (browse)'),
        'field_id': fields.many2one('ir.model.fields', 'Field', help='Select field property'),
    }

    _defaults = {
        'expression': lambda *a: 'True',
        'sequence': lambda *a: 100,
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
    _columns = {
        'name': fields.char('Company Name', size=64, required=True),
        'parent_id': fields.many2one('res.company', 'Parent Company', select=True),
        'child_ids': fields.one2many('res.company', 'parent_id', 'Child Companies'),
        'partner_id': fields.many2one('res.partner', 'Partner', required=True),
        'rml_header1': fields.char('Report Header', size=200),
        'rml_footer1': fields.char('Report Footer 1', size=200),
        'rml_footer2': fields.char('Report Footer 2', size=200),
        'rml_header' : fields.text('RML Header', required=True),
        'rml_header2' : fields.text('RML Internal Header', required=True),
        'rml_header3' : fields.text('RML Internal Header', required=True),
        'logo' : fields.binary('Logo'),
        'currency_id': fields.many2one('res.currency', 'Currency', required=True),
        'currency_ids': fields.one2many('res.currency', 'company_id', 'Currency'),
        'user_ids': fields.many2many('res.users', 'res_company_users_rel', 'cid', 'user_id', 'Accepted Users'),
        'account_no':fields.char('Account No.', size=64),
    }

    def _search(self, cr, uid, args, offset=0, limit=None, order=None,
            context=None, count=False, access_rights_uid=None):

        if context is None:
            context = {}
        user_preference = context.get('user_preference', False)
        if user_preference:
            # We browse as superuser. Otherwise, the user would be able to
            # select only the currently visible companies (according to rules,
            # which are probably to allow to see the child companies) even if
            # she belongs to some other companies.
            user = self.pool.get('res.users').browse(cr, 1, uid, context=context)
            cmp_ids = list(set([user.company_id.id] + [cmp.id for cmp in user.company_ids]))
            return cmp_ids
        return super(res_company, self)._search(cr, uid, args, offset=offset, limit=limit, order=order,
            context=context, count=count, access_rights_uid=access_rights_uid)

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
        ]

        ids = proxy.search(cr, uid, args, context=context)
        user = self.pool.get('res.users').browse(cr, uid, uid, context=context)
        for rule in proxy.browse(cr, uid, ids, context):
            if eval(rule.expression, {'context': context, 'user': user}):
                return rule.company_dest_id.id
        return user.company_id.id

    def _get_child_ids(self, cr, uid, uid2, context={}):
        company = self.pool.get('res.users').company_get(cr, uid, uid2)
        ids = self._get_company_children(cr, uid, company)
        return ids

    @tools.cache()
    def _get_company_children(self, cr, uid=None, company=None):
        if not company:
            return []
        ids =  self.search(cr, uid, [('parent_id','child_of',[company])])
        return ids

    def _get_partner_hierarchy(self, cr, uid, company_id, context={}):
        if company_id:
            parent_id = self.browse(cr, uid, company_id)['parent_id']
            if parent_id:
                return self._get_partner_hierarchy(cr, uid, parent_id.id, context)
            else:
                return self._get_partner_descendance(cr, uid, company_id, [], context)
        return []

    def _get_partner_descendance(self, cr, uid, company_id, descendance, context={}):
        descendance.append(self.browse(cr, uid, company_id).partner_id.id)
        for child_id in self._get_company_children(cr, uid, company_id):
            if child_id != company_id:
                descendance = self._get_partner_descendance(cr, uid, child_id, descendance)
        return descendance

    #
    # This function restart the cache on the _get_company_children method
    #
    def cache_restart(self, cr):
        self._get_company_children.clear_cache(cr.dbname)

    def create(self, cr, uid, vals, context=None):
        if not vals.get('name', False) or vals.get('partner_id', False):
            self.cache_restart(cr)
            return super(res_company, self).create(cr, uid, vals, context=context)
        obj_partner = self.pool.get('res.partner')
        partner_id = obj_partner.create(cr, uid, {'name': vals['name']}, context=context)
        vals.update({'partner_id': partner_id})
        self.cache_restart(cr)
        company_id = super(res_company, self).create(cr, uid, vals, context=context)
        obj_partner.write(cr, uid, partner_id, {'company_id': company_id}, context=context)
        return company_id

    def write(self, cr, *args, **argv):
        self.cache_restart(cr)
        return super(res_company, self).write(cr, *args, **argv)

    def _get_euro(self, cr, uid, context={}):
        try:
            return self.pool.get('res.currency').search(cr, uid, [])[0]
        except:
            return False

    def _get_logo(self, cr, uid, ids):
        return open(os.path.join(
            tools.config['root_path'], '..', 'pixmaps', 'openerp-header.png'),
                    'rb') .read().encode('base64')

    def _get_header3(self,cr,uid,ids):
        return """
<header>
<pageTemplate>
    <frame id="first" x1="28.0" y1="28.0" width="786" height="525"/>
    <pageGraphics>
        <fill color="black"/>
        <stroke color="black"/>
        <setFont name="DejaVu Sans" size="8"/>
        <drawString x="25" y="555"> [[ formatLang(time.strftime("%Y-%m-%d"), date=True) ]]  [[ time.strftime("%H:%M") ]]</drawString>
        <setFont name="DejaVu Sans Bold" size="10"/>
        <drawString x="382" y="555">[[ company.partner_id.name ]]</drawString>
        <stroke color="#000000"/>
        <lines>25 550 818 550</lines>
    </pageGraphics>
    </pageTemplate>
</header>"""
    def _get_header2(self,cr,uid,ids):
        return """
        <header>
        <pageTemplate>
        <frame id="first" x1="28.0" y1="28.0" width="539" height="772"/>
        <pageGraphics>
        <fill color="black"/>
        <stroke color="black"/>
        <setFont name="DejaVu Sans" size="8"/>
        <drawString x="1.0cm" y="28.3cm"> [[ formatLang(time.strftime("%Y-%m-%d"), date=True) ]]  [[ time.strftime("%H:%M") ]]</drawString>
        <setFont name="DejaVu Sans Bold" size="10"/>
        <drawString x="9.3cm" y="28.3cm">[[ company.partner_id.name ]]</drawString>
        <stroke color="#000000"/>
        <lines>1.0cm 28.1cm 20.1cm 28.1cm</lines>
        </pageGraphics>
        </pageTemplate>
</header>"""
    def _get_header(self,cr,uid,ids):
        try :
            header_file = tools.file_open(os.path.join('base', 'report', 'corporate_rml_header.rml'))
            try:
                return header_file.read()
            finally:
                header_file.close()
        except:
            return """
    <header>
    <pageTemplate>
        <frame id="first" x1="1.3cm" y1="2.5cm" height="23.0cm" width="19cm"/>
        <pageGraphics>
            <!-- You Logo - Change X,Y,Width and Height -->
            <image x="1.3cm" y="27.6cm" height="40.0" >[[ company.logo or removeParentNode('image') ]]</image>
            <setFont name="DejaVu Sans" size="8"/>
            <fill color="black"/>
            <stroke color="black"/>
            <lines>1.3cm 27.7cm 20cm 27.7cm</lines>

            <drawRightString x="20cm" y="27.8cm">[[ company.rml_header1 ]]</drawRightString>


            <drawString x="1.3cm" y="27.2cm">[[ company.partner_id.name ]]</drawString>
            <drawString x="1.3cm" y="26.8cm">[[ company.partner_id.address and company.partner_id.address[0].street or  '' ]]</drawString>
            <drawString x="1.3cm" y="26.4cm">[[ company.partner_id.address and company.partner_id.address[0].zip or '' ]] [[ company.partner_id.address and company.partner_id.address[0].city or '' ]] - [[ company.partner_id.address and company.partner_id.address[0].country_id and company.partner_id.address[0].country_id.name  or '']]</drawString>
            <drawString x="1.3cm" y="26.0cm">Phone:</drawString>
            <drawRightString x="7cm" y="26.0cm">[[ company.partner_id.address and company.partner_id.address[0].phone or '' ]]</drawRightString>
            <drawString x="1.3cm" y="25.6cm">Mail:</drawString>
            <drawRightString x="7cm" y="25.6cm">[[ company.partner_id.address and company.partner_id.address[0].email or '' ]]</drawRightString>
            <lines>1.3cm 25.5cm 7cm 25.5cm</lines>

            <!--page bottom-->

            <lines>1.2cm 2.15cm 19.9cm 2.15cm</lines>

            <drawCentredString x="10.5cm" y="1.7cm">[[ company.rml_footer1 ]]</drawCentredString>
            <drawCentredString x="10.5cm" y="1.25cm">[[ company.rml_footer2 ]]</drawCentredString>
            <drawCentredString x="10.5cm" y="0.8cm">Contact : [[ user.name ]] - Page: <pageNumber/></drawCentredString>
        </pageGraphics>
    </pageTemplate>
</header>"""
    _defaults = {
        'currency_id': _get_euro,
        'rml_header':_get_header,
        'rml_header2': _get_header2,
        'rml_header3': _get_header3,
        #'logo':_get_logo
    }

    _constraints = [
        (osv.osv._check_recursion, 'Error! You can not create recursive companies.', ['parent_id'])
    ]

    def createReport(self, cr, uid, ids, context=None):
        company = self.browse(cr, uid, ids)[0]
        rml = etree.XML(company.rml_header)
        rml = rml.getchildren()[0]
        header_xml = """<document filename="Preview Report.pdf">
        <template pageSize="(595.0,842.0)" title="Preview Report" author="OpenERP S.A.(sales@openerp.com)" allowSplitting="20">""" + etree.tostring(rml) +  """
          </template>
          </document>
          """
        tmppath= '/tmp/previews.rml'
        fp = open(tmppath, 'wb+')
        fp.write(header_xml)
        fp.close()
        if not netsvc.Service._services.get('report.comapany.report'):
            myreport = report_sxw.report_sxw('report.comapany.report', 'res.company', tmppath,  header=False)
        return {
                'type': 'ir.actions.report.xml',
                'report_name': 'comapany.report',
                'datas': {'ids': ids, 'model': 'res.company'},
                'nodestroy': True
            }

res_company()


# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:



