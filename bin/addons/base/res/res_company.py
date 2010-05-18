# -*- encoding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution	
#    Copyright (C) 2004-2009 Tiny SPRL (<http://tiny.be>). All Rights Reserved
#    $Id$
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################

from osv import fields,osv
import os
import tools

class res_company(osv.osv):
    _name = "res.company"

    _columns = {
        'name': fields.char('Company Name', size=64, required=True),
        'parent_id': fields.many2one('res.company', 'Parent Company', select=True),
        'child_ids': fields.one2many('res.company', 'parent_id', 'Child Companies'),
        'partner_id': fields.many2one('res.partner', 'Partner', required=True),
        'rml_header1': fields.char('Report Header', size=200),
        'rml_footer1': fields.char('Report Footer 1', size=200),
        'rml_footer2': fields.char('Report Footer 2', size=200),
        'rml_header' : fields.text('RML Header'),
        'rml_header2' : fields.text('RML Internal Header'),
        'logo' : fields.binary('Logo'),
        'currency_id': fields.many2one('res.currency', 'Currency', required=True),
    }
    
    def _get_child_ids(self, cr, uid, uid2, context={}):
        company = self.pool.get('res.users').company_get(cr, uid, uid2)
        ids = self._get_company_children(cr, uid, company)
        return ids

    def _get_company_children(self, cr, uid=None, company=None):
        if not company:
            return []
        ids =  self.search(cr, uid, [('parent_id','child_of',[company])])
        return ids
    _get_company_children = tools.cache()(_get_company_children)

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

    def create(self, cr, *args, **argv):
        self.cache_restart(cr)
        return super(res_company, self).create(cr, *args, **argv)

    def write(self, cr, *args, **argv):
        self.cache_restart(cr)
        # Restart the cache on the company_get method
        return super(res_company, self).write(cr, *args, **argv)

    def _get_euro(self, cr, uid, context={}):
        try:
            return self.pool.get('res.currency').search(cr, uid, [])[0]
        except:
            return False
    
    def _check_recursion(self, cr, uid, ids):
        level = 100
        while len(ids):
            cr.execute('select distinct parent_id from res_company where id in %s', (tuple(ids),))
            ids = filter(None, map(lambda x:x[0], cr.fetchall()))
            if not level:
                return False
            level -= 1
        return True
    
    def _get_header2(self,cr,uid,ids):
        return """
        <header>
        <pageTemplate>
        <frame id="first" x1="1.3cm" y1="1.5cm" width="18.4cm" height="26.5cm"/>
        <pageGraphics>
        <fill color="black"/>
        <stroke color="black"/>
        <setFont name="Helvetica" size="8"/>
        <drawString x="1.3cm" y="28.3cm"> [[ formatLang(time.strftime("%Y-%m-%d"), date=True) ]]  [[ time.strftime("%H:%M") ]]</drawString>
        <setFont name="Helvetica-Bold" size="10"/>
        <drawString x="9.8cm" y="28.3cm">[[ company.partner_id.name ]]</drawString>
        <setFont name="Helvetica" size="8"/>
        <drawRightString x="19.7cm" y="28.3cm"><pageNumber/> /  </drawRightString>
        <drawString x="19.8cm" y="28.3cm"><pageCount/></drawString>
        <stroke color="#000000"/>
        <lines>1.3cm 28.1cm 20cm 28.1cm</lines>
        </pageGraphics>
        </pageTemplate>
</header>"""
    def _get_header(self,cr,uid,ids):
        try :
            return tools.file_open(os.path.join('base', 'report', 'corporate_rml_header.rml')).read()
        except:
            return """
    <header>
    <pageTemplate>
        <frame id="first" x1="1.3cm" y1="2.5cm" height="23.0cm" width="19cm"/>
        <pageGraphics>
            <!-- You Logo - Change X,Y,Width and Height -->
        <image x="1.3cm" y="27.6cm" height="40.0" >[[company.logo]]</image>
            <setFont name="Helvetica" size="8"/>
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
        'rml_header2': _get_header2
    }

    _constraints = [
        (_check_recursion, 'Error! You can not create recursive companies.', ['parent_id'])
    ]

res_company()


# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:

