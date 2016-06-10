# -*- encoding: utf-8 -*-
##############################################################################
#
#    Odoo, Open Source Business Applications
#    Copyright (C) 2014-2015 Odoo S.A. <http://www.odoo.com>
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
#    along with this program. If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################

import base64
import xml.etree.ElementTree as ET
from collections import namedtuple
from datetime import datetime

from openerp import exceptions, SUPERUSER_ID, tools
from openerp.osv import fields, osv
from openerp.tools.translate import _

INTRASTAT_XMLNS = 'http://www.onegate.eu/2010-01-01'

class xml_decl(osv.TransientModel):
    """
    Intrastat XML Declaration
    """
    _name = "l10n_be_intrastat_xml.xml_decl"
    _description = 'Intrastat XML Declaration'

    def _get_tax_code(self, cr, uid, context=None):
        obj_tax_code = self.pool.get('account.tax.code')
        obj_user = self.pool.get('res.users')
        company_id = obj_user.browse(cr, uid, uid, context=context).company_id.id
        tax_code_ids = obj_tax_code.search(cr, uid, [('company_id', '=', company_id),
                                                     ('parent_id', '=', False)],
                                           context=context)
        return tax_code_ids and tax_code_ids[0] or False

    def _get_def_monthyear(self, cr, uid, context=None):
        td = datetime.strptime(fields.date.context_today(self, cr, uid, context=context),
                               tools.DEFAULT_SERVER_DATE_FORMAT).date()
        return td.strftime('%Y'), td.strftime('%m')

    def _get_def_month(self, cr, uid, context=None):
        return self._get_def_monthyear(cr, uid, context=context)[1]

    def _get_def_year(self, cr, uid, context=None):
        return self._get_def_monthyear(cr, uid, context=context)[0]

    _columns = {
        'name': fields.char('File Name'),
        'month': fields.selection([('01','January'), ('02','February'), ('03','March'),
                                   ('04','April'), ('05','May'), ('06','June'), ('07','July'),
                                   ('08','August'), ('09','September'), ('10','October'),
                                   ('11','November'), ('12','December')], 'Month', required=True),
        'year': fields.char('Year', size=4, required=True),
        'tax_code_id': fields.many2one('account.tax.code', 'Company Tax Chart',
                                       domain=[('parent_id', '=', False)], required=True),
        'arrivals': fields.selection([('be-exempt', 'Exempt'),
                                      ('be-standard', 'Standard'),
                                      ('be-extended', 'Extended')],
                                     'Arrivals', required=True),
        'dispatches': fields.selection([('be-exempt', 'Exempt'),
                                      ('be-standard', 'Standard'),
                                      ('be-extended', 'Extended')],
                                       'Dispatches', required=True),
        'file_save': fields.binary('Intrastat Report File', readonly=True),
        'state': fields.selection([('draft', 'Draft'), ('download', 'Download')], string="State"),
    }

    _defaults = {
        'arrivals': 'be-standard',
        'dispatches': 'be-standard',
        'name': 'intrastat.xml',
        'tax_code_id': _get_tax_code,
        'month': _get_def_month,
        'year': _get_def_year,
        'state': 'draft',
    }
    
    def _company_warning(self, cr, uid, translated_msg, context=None):
        """ Raise a error with custom message, asking user to configure company settings """
        xmlid_mod = self.pool['ir.model.data']
        action_id = xmlid_mod.xmlid_to_res_id(cr, uid, 'base.action_res_company_form')
        raise exceptions.RedirectWarning(
            translated_msg, action_id, _('Go to company configuration screen'))
            
    def create_xml(self, cr, uid, ids, context=None):
        """Creates xml that is to be exported and sent to estate for partner vat intra.
        :return: Value for next action.
        :rtype: dict
        """
        decl_datas = self.browse(cr, uid, ids[0])
        company = decl_datas.tax_code_id.company_id
        if not (company.partner_id and company.partner_id.country_id and
                company.partner_id.country_id.id):
            self._company_warning(
                cr, uid,
                _('The country of your company is not set, '
                  'please make sure to configure it first.'),
                context=context)
        kbo = company.company_registry
        if not kbo:
            self._company_warning(
                cr, uid,
                _('The registry number of your company is not set, '
                  'please make sure to configure it first.'),
                context=context)
        if len(decl_datas.year) != 4:
            raise exceptions.Warning(_('Year must be 4 digits number (YYYY)'))

        #Create root declaration
        decl = ET.Element('DeclarationReport')
        decl.set('xmlns', INTRASTAT_XMLNS)

        #Add Administration elements
        admin = ET.SubElement(decl, 'Administration')
        fromtag = ET.SubElement(admin, 'From')
        fromtag.text = kbo
        fromtag.set('declarerType', 'KBO')
        ET.SubElement(admin, 'To').text = "NBB"
        ET.SubElement(admin, 'Domain').text = "SXX"
        if decl_datas.arrivals == 'be-standard':
            decl.append(self._get_lines(cr, SUPERUSER_ID, ids, decl_datas, company,
                                        dispatchmode=False, extendedmode=False, context=context))
        elif decl_datas.arrivals == 'be-extended':
            decl.append(self._get_lines(cr, SUPERUSER_ID, ids, decl_datas, company,
                                        dispatchmode=False, extendedmode=True, context=context))
        if decl_datas.dispatches == 'be-standard':
            decl.append(self._get_lines(cr, SUPERUSER_ID, ids, decl_datas, company,
                                        dispatchmode=True, extendedmode=False, context=context))
        elif decl_datas.dispatches == 'be-extended':
            decl.append(self._get_lines(cr, SUPERUSER_ID, ids, decl_datas, company,
                                        dispatchmode=True, extendedmode=True, context=context))

        #Get xml string with declaration
        data_file = ET.tostring(decl, encoding='UTF-8', method='xml')

        #change state of the wizard
        self.write(cr, uid, ids,
                   {'name': 'intrastat_%s%s.xml' % (decl_datas.year, decl_datas.month),
                    'file_save': base64.encodestring(data_file),
                    'state': 'download'},
                   context=context)
        return {
            'name': _('Save'),
            'context': context,
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'l10n_be_intrastat_xml.xml_decl',
            'type': 'ir.actions.act_window',
            'target': 'new',
            'res_id': ids[0],
        }

    def _get_lines(self, cr, uid, ids, decl_datas, company, dispatchmode=False,
                   extendedmode=False, context=None):
        intrastatcode_mod = self.pool['report.intrastat.code']
        invoiceline_mod = self.pool['account.invoice.line']
        product_mod = self.pool['product.product']
        region_mod = self.pool['l10n_be_intrastat.region']
        warehouse_mod = self.pool['stock.warehouse']

        if dispatchmode:
            mode1 = 'out_invoice'
            mode2 = 'in_refund'
            declcode = "29"
        else:
            mode1 = 'in_invoice'
            mode2 = 'out_refund'
            declcode = "19"

        decl = ET.Element('Report')
        if not extendedmode:
            decl.set('code', 'EX%sS' % declcode)
        else:
            decl.set('code', 'EX%sE' % declcode)
        decl.set('date', '%s-%s' % (decl_datas.year, decl_datas.month))
        datas = ET.SubElement(decl, 'Data')
        if not extendedmode:
            datas.set('form', 'EXF%sS' % declcode)
        else:
            datas.set('form', 'EXF%sE' % declcode)
        datas.set('close', 'true')
        intrastatkey = namedtuple("intrastatkey",
                                  ['EXTRF', 'EXCNT', 'EXTTA', 'EXREG',
                                   'EXGO', 'EXTPC', 'EXDELTRM'])
        entries = {}

        sqlreq = """
            select
                inv_line.id
            from
                account_invoice_line inv_line
                join account_invoice inv on inv_line.invoice_id=inv.id
                left join res_country on res_country.id = inv.intrastat_country_id
                left join res_partner on res_partner.id = inv.partner_id
                left join res_country countrypartner on countrypartner.id = res_partner.country_id
                join product_product on inv_line.product_id=product_product.id
                join product_template on product_product.product_tmpl_id=product_template.id
                left join account_period on account_period.id=inv.period_id
            where
                inv.state in ('open','paid')
                and inv.company_id=%s
                and not product_template.type='service'
                and (res_country.intrastat=true or (inv.intrastat_country_id is null
                                                    and countrypartner.intrastat=true))
                and ((res_country.code is not null and not res_country.code=%s)
                     or (res_country.code is null and countrypartner.code is not null
                     and not countrypartner.code=%s))
                and inv.type in (%s, %s)
                and to_char(account_period.date_start, 'YYYY')=%s
                and to_char(account_period.date_start, 'MM')=%s
            """

        cr.execute(sqlreq, (company.id, company.partner_id.country_id.code,
                            company.partner_id.country_id.code, mode1, mode2,
                            decl_datas.year, decl_datas.month))
        lines = cr.fetchall()
        invoicelines_ids = [rec[0] for rec in lines]
        invoicelines = invoiceline_mod.browse(cr, uid, invoicelines_ids, context=context)
        for inv_line in invoicelines:

            #Check type of transaction
            if inv_line.invoice_id.intrastat_transaction_id:
                extta = inv_line.invoice_id.intrastat_transaction_id.code
            else:
                extta = "1"
            #Check country
            if inv_line.invoice_id.intrastat_country_id:
                excnt = inv_line.invoice_id.intrastat_country_id.code
            else:
                excnt = inv_line.invoice_id.partner_id.country_id.code

            #Check region
            #If purchase, comes from purchase order, linked to a location,
            #which is linked to the warehouse
            #if sales, the sale order is linked to the warehouse
            #if sales, from a delivery order, linked to a location,
            #which is linked to the warehouse
            #If none found, get the company one.
            exreg = None
            if inv_line.invoice_id.type in ('in_invoice', 'in_refund'):
                #comes from purchase
                POL = self.pool['purchase.order.line']
                poline_ids = POL.search(
                    cr, uid, [('invoice_lines', 'in', inv_line.id)], context=context)
                if poline_ids:
                    purchaseorder = POL.browse(cr, uid, poline_ids[0], context=context).order_id
                    region_id = warehouse_mod.get_regionid_from_locationid(
                        cr, uid, purchaseorder.location_id.id, context=context)
                    if region_id:
                        exreg = region_mod.browse(cr, uid, region_id).code
            elif inv_line.invoice_id.type in ('out_invoice', 'out_refund'):
                #comes from sales
                soline_ids = self.pool['sale.order.line'].search(
                    cr, uid, [('invoice_lines', 'in', inv_line.id)], context=context)
                if soline_ids:
                    saleorder = self.pool['sale.order.line'].browse(
                        cr, uid, soline_ids[0], context=context).order_id
                    if saleorder and saleorder.warehouse_id and saleorder.warehouse_id.region_id:
                        exreg = region_mod.browse(
                            cr, uid, saleorder.warehouse_id.region_id.id, context=context).code

            if not exreg:
                if company.region_id:
                    exreg = company.region_id.code
                else:
                    self._company_warning(
                        cr, uid,
                        _('The Intrastat Region of the selected company is not set, '
                          'please make sure to configure it first.'),
                        context=context)

            #Check commodity codes
            intrastat_id = product_mod.get_intrastat_recursively(
                cr, uid, inv_line.product_id.id, context=context)
            if intrastat_id:
                exgo = intrastatcode_mod.browse(cr, uid, intrastat_id, context=context).name
            else:
                raise exceptions.Warning(
                    _('Product "%s" has no intrastat code, please configure it') %
                        inv_line.product_id.display_name)

            #In extended mode, 2 more fields required
            if extendedmode:
                #Check means of transport
                if inv_line.invoice_id.transport_mode_id:
                    extpc = inv_line.invoice_id.transport_mode_id.code
                elif company.transport_mode_id:
                    extpc = company.transport_mode_id.code
                else:
                    self._company_warning(
                        cr, uid,
                        _('The default Intrastat transport mode of your company '
                          'is not set, please make sure to configure it first.'),
                        context=context)

                #Check incoterm
                if inv_line.invoice_id.incoterm_id:
                    exdeltrm = inv_line.invoice_id.incoterm_id.code
                elif company.incoterm_id:
                    exdeltrm = company.incoterm_id.code
                else:
                    self._company_warning(
                        cr, uid,
                        _('The default Incoterm of your company is not set, '
                          'please make sure to configure it first.'),
                        context=context)
            else:
                extpc = ""
                exdeltrm = ""
            linekey = intrastatkey(EXTRF=declcode, EXCNT=excnt,
                                   EXTTA=extta, EXREG=exreg, EXGO=exgo,
                                   EXTPC=extpc, EXDELTRM=exdeltrm)
            #We have the key
            #calculate amounts
            if inv_line.price_unit and inv_line.quantity:
                amount = inv_line.price_unit * inv_line.quantity
            else:
                amount = 0
            weight = (inv_line.product_id.weight_net or 0.0) * \
                self.pool.get('product.uom')._compute_qty(cr, uid, inv_line.uos_id.id, inv_line.quantity, inv_line.product_id.uom_id.id)
            if (not inv_line.uos_id.category_id or not inv_line.product_id.uom_id.category_id
                    or inv_line.uos_id.category_id.id != inv_line.product_id.uom_id.category_id.id):
                supply_units = inv_line.quantity
            else:
                supply_units = inv_line.quantity * inv_line.uos_id.factor
            amounts = entries.setdefault(linekey, (0, 0, 0))
            amounts = (amounts[0] + amount, amounts[1] + weight, amounts[2] + supply_units)
            entries[linekey] = amounts

        numlgn = 0
        for linekey in entries:
            numlgn += 1
            amounts = entries[linekey]
            item = ET.SubElement(datas, 'Item')
            self._set_Dim(item, 'EXSEQCODE', unicode(numlgn))
            self._set_Dim(item, 'EXTRF', unicode(linekey.EXTRF))
            self._set_Dim(item, 'EXCNT', unicode(linekey.EXCNT))
            self._set_Dim(item, 'EXTTA', unicode(linekey.EXTTA))
            self._set_Dim(item, 'EXREG', unicode(linekey.EXREG))
            self._set_Dim(item, 'EXTGO', unicode(linekey.EXGO))
            if extendedmode:
                self._set_Dim(item, 'EXTPC', unicode(linekey.EXTPC))
                self._set_Dim(item, 'EXDELTRM', unicode(linekey.EXDELTRM))
            self._set_Dim(item, 'EXTXVAL', unicode(round(amounts[0], 0)).replace(".", ","))
            self._set_Dim(item, 'EXWEIGHT', unicode(round(amounts[1], 0)).replace(".", ","))
            self._set_Dim(item, 'EXUNITS', unicode(round(amounts[2], 0)).replace(".", ","))

        if numlgn == 0:
            #no datas
            datas.set('action', 'nihil')
        return decl

    def _set_Dim(self, item, prop, value):
        dim = ET.SubElement(item, 'Dim')
        dim.set('prop', prop)
        dim.text = value
