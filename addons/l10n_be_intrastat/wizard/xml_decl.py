# -*- encoding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2004-TODAY OpenERP S.A. <http://www.odoo.com>
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
import base64
import time
import xml.etree.ElementTree as ET
from collections import namedtuple
from datetime import date, datetime, timedelta

from openerp import exceptions, SUPERUSER_ID, tools
from openerp.osv import fields, osv
from openerp.report import report_sxw
from openerp.tools.translate import _


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
        tax_code_ids = obj_tax_code.search(cr, uid, [('company_id', '=', company_id), ('parent_id', '=', False)], context=context)
        return tax_code_ids and tax_code_ids[0] or False

    def _get_def_monthyear(self, cr, uid, context=None):
        td = datetime.strptime(fields.date.context_today(self, cr, uid, context=context), tools.DEFAULT_SERVER_DATE_FORMAT).date()
        #date.today()
        return td.year, td.month

    def _get_def_month(self, cr, uid, context=None):
        return self._get_def_monthyear(cr, uid, context=context)[1]

    def _get_def_year(self, cr, uid, context=None):
        return self._get_def_monthyear(cr, uid, context=context)[0]

    _columns = {
        'name': fields.char('File Name', size=32),
        'month': fields.char('Month', size=2, required=True),
        'year': fields.char('Year', size=4, required=True),
        'tax_code_id': fields.many2one('account.tax.code', 'Company', domain=[('parent_id', '=', False)],
                                           help="Keep empty to use the user's company", required=True),
        'arrivals': fields.selection([('be-exempt', 'Exempt'),
                                      ('be-standard', 'Standard'),
                                      ('be-extended', 'Extended')], 'Arrivals', required=True),
        'dispatches': fields.selection([('be-exempt', 'Exempt'),
                                      ('be-standard', 'Standard'),
                                      ('be-extended', 'Extended')], 'Dispatches', required=True),
        'decl_xml': fields.boolean('Intrastat XML file', help="Sets the XML output"),
        'msg': fields.text('File created', size=14, readonly=True),
        'file_save': fields.binary('Save File', readonly=True),
        'comments': fields.text('Comments'),
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

    def create_xml(self, cr, uid, ids, context=None):
        """Creates xml that is to be exported and sent to estate for partner vat intra.
        :return: Value for next action.
        :rtype: dict
        """

        decl_datas = self.browse(cr, uid, ids[0])
        company = decl_datas.tax_code_id.company_id
        if not (company.partner_id and company.partner_id.country_id and company.partner_id.country_id.id):
            model, action_id = self.pool['ir.model.data'].get_object_reference(cr, uid, 'base', 'action_res_company_form')
            raise exceptions.RedirectWarning(_('Insufficient Data!\nNo Country associated with your company.'), action_id, _('Go to the companies configuration'))
        kbo = company.company_registry
        if not kbo:
            model, action_id = self.pool['ir.model.data'].get_object_reference(cr, uid, 'base', 'action_res_company_form')
            raise exceptions.RedirectWarning(_('Insufficient Data!\nNo company registry associated with your company.'), action_id, _('Go to the companies configuration'))
        if len(decl_datas.month) != 2:
            decl_datas.month = "0%s" % decl_datas.month
        if int(decl_datas.month)<1 or int(decl_datas.month)>12:
            raise osv.except_osv(_('Incorrect Data!'), _('Month is a number between 1 and 12.'))
        if len(decl_datas.year) != 4:
            raise osv.except_osv(_('Incorrect Data!'), _('Year is a number of 4 digits.'))

        #Create root declaration
        decl = ET.Element('DeclarationReport')
        decl.set('xmlns', 'http://www.onegate.eu/2010-01-01')

        #Add Administration elements
        admin = ET.SubElement(decl, 'Administration')
        fromtag = ET.SubElement(admin, 'From')
        fromtag.text = kbo
        fromtag.set('declarerType', 'KBO')
        ET.SubElement(admin, 'To').text = "NBB"
        ET.SubElement(admin, 'Domain').text = "SXX"
        if decl_datas.arrivals == 'be-standard':
            decl.append(self._get_lines(cr, SUPERUSER_ID, ids, decl_datas, company, dispatchmode=False, extendedmode=False, context=context))
        elif decl_datas.arrivals == 'be-extended':
            decl.append(self._get_lines(cr, SUPERUSER_ID, ids, decl_datas, company, dispatchmode=False, extendedmode=True, context=context))
        if decl_datas.dispatches == 'be-standard':
            decl.append(self._get_lines(cr, SUPERUSER_ID, ids, decl_datas, company, dispatchmode=True, extendedmode=False, context=context))
        elif decl_datas.dispatches == 'be-extended':
            decl.append(self._get_lines(cr, SUPERUSER_ID, ids, decl_datas, company, dispatchmode=True, extendedmode=True, context=context))

        #Get xml string with declaration
        data_file = ET.tostring(decl, encoding='UTF-8', method='xml')

        #change state of the wizard
        self.write(cr, uid, ids, {'file_save' : base64.encodestring(data_file), 'state' : 'download'}, context=context)
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

    def _get_lines(self, cr, uid, ids, decl_datas, company, dispatchmode=False, extendedmode=False, context=None):
        curr_mod = self.pool['res.currency']
        incoterm_mod = self.pool['stock.incoterms']
        intrastatcode_mod = self.pool['report.intrastat.code']
        invoice_mod = self.pool['account.invoice']
        invoiceline_mod = self.pool['account.invoice.line']
        location_mod = self.pool['stock.location']
        product_mod = self.pool['product.product']
        purchaseorder_mod = self.pool['purchase.order']
        region_mod = self.pool['l10n_be_intrastat.regions']
        saleorder_mod = self.pool['sale.order']
        trans_mod = self.pool['l10n_be_intrastat.transport_mode']
        warehouse_mod = self.pool['stock.warehouse']
        picking_mod = self.pool['stock.picking']

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
        intrastatkey = namedtuple("intrastatkey", ['EXTRF','EXCNT','EXTTA','EXREG','EXGO','EXTPC','EXDELTRM'])
        entries = {}

        sqlreq = """
            select
                distinct inv_line.id
            from
                account_invoice inv
                inner join account_invoice_line inv_line on inv_line.invoice_id=inv.id
                left join res_country on res_country.id = inv.intrastat_country_id
                left join res_partner on res_partner.id = inv.partner_id
                left join res_country countrypartner on countrypartner.id = res_partner.country_id
                inner join product_product on inv_line.product_id=product_product.id
                inner join product_template on product_product.product_tmpl_id=product_template.id
            where
                inv.state in ('open','paid')
                and not product_template.type='service'
                and (res_country.intrastat=true or (inv.intrastat_country_id is null and countrypartner.intrastat=true))
                and ((res_country.code is not null and not res_country.code=%s) or (res_country.code is null and countrypartner.code is not null and not countrypartner.code=%s))
                and inv.type in (%s, %s)
                and to_char(inv.create_date, 'YYYY')=%s
                and to_char(inv.create_date, 'MM')=%s
                and inv.company_id=%s
            """

        cr.execute(sqlreq, (company.partner_id.country_id.code, company.partner_id.country_id.code, mode1, mode2, decl_datas.year, decl_datas.month, company.id))
        lines = cr.fetchall()
        invoicelines_ids = [rec[0] for rec in lines]
        invoicelines = invoiceline_mod.browse(cr, uid, invoicelines_ids, context=context)
        for invoiceline in invoicelines:

            #Check type of transaction
            if invoiceline.invoice_id.intrastat_transaction_id:
                extta = invoiceline.invoice_id.intrastat_transaction_id.code
            else:
                extta = "1"
            #Check country
            if invoiceline.invoice_id.intrastat_country_id:
                excnt = invoiceline.invoice_id.intrastat_country_id.code
            else:
                excnt = invoiceline.invoice_id.partner_id.country_id.code

            #Check region
            #If purchase, comes from purchase order, linked to a location,
            #which is linked to the warehouse
            #if sales, the sale order is linked to the warehouse
            #if sales, from a delivery order, linked to a location,
            #which is linked to the warehouse
            #If none found, get the company one.
            exreg = None
            if invoiceline.invoice_id.type in ('in_invoice', 'in_refund'):
                #comes from purchase
                if invoiceline.invoice_id.origin:
                    po_ids = purchaseorder_mod.search(cr, SUPERUSER_ID, ([('company_id', '=', company.id), ('name', '=', invoiceline.invoice_id.origin)]), context=context)
                    if po_ids and po_ids[0]:
                        purchaseorder = purchaseorder_mod.browse(cr, SUPERUSER_ID, po_ids[0])
                        region_id = warehouse_mod.get_regionid_from_locationid(cr, uid, purchaseorder.location_id.id, context=context)
                        if region_id:
                            exreg = region_mod.browse(cr, uid, region_id).code
            elif invoiceline.invoice_id.type in ('out_invoice', 'out_refund'):
                #comes from sales
                if invoiceline.invoice_id.origin:
                    so_ids = saleorder_mod.search(cr, uid, ([('company_id', '=', company.id), ('name', '=', invoiceline.invoice_id.origin)]), context=context)
                    if so_ids and so_ids[0]:
                        saleorder = saleorder_mod.browse(cr, uid, so_ids[0], context=context)
                        if saleorder and saleorder.warehouse_id and saleorder.warehouse_id.region_id:
                            exreg = region_mod.browse(cr, uid, saleorder.warehouse_id.region_id.id, context=context).code
                    else:
                        #search on deliveries
                        delivery_ids = picking_mod.search(cr, uid, ([('company_id', '=', company.id), ('name', '=', invoiceline.invoice_id.origin)]), context=context)
                        if delivery_ids and delivery_ids[0]:
                            delivery = picking_mod.browse(cr, uid, delivery_ids[0], context=context)
                            if delivery and delivery.location_id and delivery.location_id[0]:
                                region_id = warehouse_mod.get_regionid_from_locationid(cr, uid, delivery.location_id[0].id, context=context)
                                if region_id:
                                    exreg = region_mod.browse(cr, uid, region_id).code

            if not exreg:
                if company.region_id:
                    exreg = company.region_id.code
                else:
                    model, action_id = self.pool['ir.model.data'].get_object_reference(cr, uid, 'base', 'action_res_company_form')
                    raise exceptions.RedirectWarning(_('Please set the intrastat region for your company.\nThis can be done in the Settings menu.'), action_id, _('Go to the companies configuration'))

            #Check commodity codes
            intrastat_id = product_mod.get_intrastat_recursively(cr, uid, invoiceline.product_id.id, context=context)
            if intrastat_id:
                exgo = intrastatcode_mod.browse(cr, uid, intrastat_id, context=context).name
            else:
                raise osv.except_osv(_('Incorrect Data!'), _('Product %s has no intrastat code') % (invoiceline.product_id.name))

            #In extended mode, 2 more fields required
            if extendedmode:
                #Check means of transport
                if invoiceline.invoice_id.transport_mode_id:
                    extpc = invoiceline.invoice_id.transport_mode_id.code
                elif company.transport_mode_id:
                    extpc = company.transport_mode_id.code
                else:
                    model, action_id = self.pool['ir.model.data'].get_object_reference(cr, uid, 'base', 'action_res_company_form')
                    raise exceptions.RedirectWarning(_('Please define the default intrastat transport mode for your company.\nThis can be done in the Settings menu.'), action_id, _('Go to the companies configuration'))

                #Check incoterm
                if invoiceline.invoice_id.incoterm_id:
                    exdeltrm = invoiceline.invoice_id.incoterm_id.code
                elif company.incoterm_id:
                    exdeltrm = company.incoterm_id.code
                else:
                    model, action_id = self.pool['ir.model.data'].get_object_reference(cr, uid, 'base', 'action_res_company_form')
                    raise exceptions.RedirectWarning(_('Please define the default Incoterm for your company.\nThis can be done in the Settings menu.'), action_id, _('Go to the companies configuration'))
            else:
                extpc = ""
                exdeltrm = ""
            linekey = intrastatkey(EXTRF=declcode, EXCNT=excnt, EXTTA=extta, EXREG=exreg, EXGO=exgo, EXTPC=extpc, EXDELTRM=exdeltrm)
            #We have the key
            #calculate amounts
            if invoiceline.price_unit and invoiceline.quantity:
                amount = invoiceline.price_unit * invoiceline.quantity
            else:
                amount = 0
            if not invoiceline.uos_id.category_id or not invoiceline.product_id.uom_id.category_id or invoiceline.uos_id.category_id.id != invoiceline.product_id.uom_id.category_id.id:
                weight = invoiceline.product_id.weight_net * invoiceline.quantity
            else:
                weight = invoiceline.product_id.weight_net * invoiceline.quantity * invoiceline.uos_id.factor
            if not invoiceline.uos_id.category_id or not invoiceline.product_id.uom_id.category_id or invoiceline.uos_id.category_id.id != invoiceline.product_id.uom_id.category_id.id:
                supply_units = invoiceline.quantity
            else:
                supply_units = invoiceline.quantity * invoiceline.uos_id.factor
            amounts = entries.setdefault(linekey,(0,0,0))
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
            self._set_Dim(item, 'EXTXVAL', unicode(round(amounts[0],0)).replace(".",","))
            self._set_Dim(item, 'EXWEIGHT', unicode(round(amounts[1],0)).replace(".",","))
            self._set_Dim(item, 'EXUNITS', unicode(round(amounts[2],0)).replace(".",","))

        if numlgn == 0:
            #no datas
            datas.set('action', 'nihil')
        return decl

    def _set_Dim(self, item, prop, value):
        dim = ET.SubElement(item, 'Dim')
        dim.set('prop',prop)
        dim.text = value
