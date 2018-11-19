# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import base64
import xml.etree.ElementTree as ET
from collections import namedtuple

from odoo import api, exceptions, fields, models, _

INTRASTAT_XMLNS = 'http://www.onegate.eu/2010-01-01'


class XmlDeclaration(models.TransientModel):
    _inherit = "l10n_be_intrastat_xml.xml_decl"
    
    @api.multi
    def _get_lines(self, dispatchmode=False, extendedmode=False):
        company = self.company_id
        IntrastatRegion = self.env['l10n_be_intrastat.region']

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
        decl.set('date', '%s-%s' % (self.year, self.month))
        datas = ET.SubElement(decl, 'Data')
        if not extendedmode:
            datas.set('form', 'EXF%sS' % declcode)
        else:
            datas.set('form', 'EXF%sE' % declcode)
        datas.set('close', 'true')
        intrastatkey = namedtuple("intrastatkey",
                                  ['EXTRF', 'EXCNT', 'EXTTA', 'EXREG',
                                   'EXGO', 'EXTPC', 'EXDELTRM', 
                                   'EXCNTORI', 'PARTNERID'])
        entries = {}

        query = """
            SELECT
                inv_line.id
            FROM
                account_invoice_line inv_line
                JOIN account_invoice inv ON inv_line.invoice_id=inv.id
                LEFT JOIN res_country ON res_country.id = inv.intrastat_country_id
                LEFT JOIN res_partner ON res_partner.id = inv.partner_id
                LEFT JOIN res_country countrypartner ON countrypartner.id = res_partner.country_id
                JOIN product_product ON inv_line.product_id=product_product.id
                JOIN product_template ON product_product.product_tmpl_id=product_template.id
            WHERE
                inv.state IN ('open','paid')
                AND inv.company_id=%s
                AND not product_template.type='service'
                AND (res_country.intrastat=true OR (inv.intrastat_country_id is NULL
                                                    AND countrypartner.intrastat=true))
                AND ((res_country.code IS NOT NULL AND not res_country.code=%s)
                     OR (res_country.code is NULL AND countrypartner.code IS NOT NULL
                     AND not countrypartner.code=%s))
                AND inv.type IN (%s, %s)
                AND to_char(inv.date_invoice, 'YYYY')=%s
                AND to_char(inv.date_invoice, 'MM')=%s
            """

        self.env.cr.execute(query, (company.id, company.partner_id.country_id.code,
                            company.partner_id.country_id.code, mode1, mode2,
                            self.year, self.month))
        lines = self.env.cr.fetchall()
        invoicelines_ids = [rec[0] for rec in lines]
        invoicelines = self.env['account.invoice.line'].browse(invoicelines_ids)

        for inv_line in invoicelines:

            #Check type of transaction
            if inv_line.intrastat_transaction_id:
                extta = inv_line.intrastat_transaction_id.code
            else:
                extta = "1"
            #Check country
            if inv_line.invoice_id.intrastat_country_id:
                excnt = inv_line.invoice_id.intrastat_country_id.code
            else:
                excnt = inv_line.invoice_id.partner_shipping_id.country_id.code or inv_line.invoice_id.partner_id.country_id.code

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
                po_lines = self.env['purchase.order.line'].search([('invoice_lines', 'in', inv_line.id)], limit=1)
                if po_lines:
                    if self._is_situation_triangular(company, po_line=po_lines):
                        continue
                    location = self.env['stock.location'].browse(po_lines.order_id._get_destination_location())
                    region_id = self.env['stock.warehouse'].get_regionid_from_locationid(location)
                    if region_id:
                        exreg = IntrastatRegion.browse(region_id).code
            elif inv_line.invoice_id.type in ('out_invoice', 'out_refund'):
                #comes from sales
                so_lines = self.env['sale.order.line'].search([('invoice_lines', 'in', inv_line.id)], limit=1)
                if so_lines:
                    if self._is_situation_triangular(company, so_line=so_lines):
                        continue
                    saleorder = so_lines.order_id
                    if saleorder and saleorder.warehouse_id and saleorder.warehouse_id.region_id:
                        exreg = IntrastatRegion.browse(saleorder.warehouse_id.region_id.id).code

            if not exreg:
                if company.region_id:
                    exreg = company.region_id.code
                else:
                    self._company_warning(_('The Intrastat Region of the selected company is not set, '
                          'please make sure to configure it first.'))

            #Check commodity codes
            intrastat_id = inv_line.product_id.get_intrastat_recursively()
            if intrastat_id:
                exgo = self.env['report.intrastat.code'].browse(intrastat_id).name
            else:
                raise exceptions.Warning(
                    _('Product "%s" has no intrastat code, please configure it') % inv_line.product_id.display_name)

            #In extended mode, 2 more fields required
            if extendedmode:
                #Check means of transport
                if inv_line.invoice_id.transport_mode_id:
                    extpc = inv_line.invoice_id.transport_mode_id.code
                elif company.transport_mode_id:
                    extpc = company.transport_mode_id.code
                else:
                    self._company_warning(_('The default Intrastat transport mode of your company '
                          'is not set, please make sure to configure it first.'))

                #Check incoterm
                if inv_line.invoice_id.incoterm_id:
                    exdeltrm = inv_line.invoice_id.incoterm_id.code
                elif company.incoterm_id:
                    exdeltrm = company.incoterm_id.code
                else:
                    self._company_warning(_('The default Incoterm of your company is not set, '
                          'please make sure to configure it first.'))
            else:
                extpc = ""
                exdeltrm = ""
            
            if dispatchmode:
                if inv_line.intrastat_product_origin_country_id:
                    excntori = inv_line.intrastat_product_origin_country_id.code
                else:
                    excntori = 'QU'
                partner = self.env['res.partner'].browse(inv_line.partner_id.id)
                if partner.country_id.intrastat:
                    partnerid = partner.vat
                else:
                    partnerid = 'QV999999999999'

            
            linekey = intrastatkey(EXTRF=declcode, EXCNT=excnt,
                                   EXTTA=extta, EXREG=exreg, EXGO=exgo,
                                   EXTPC=extpc, EXDELTRM=exdeltrm,
                                   EXCNTORI=excntori, PARTNERID=partnerid)
            #We have the key
            #calculate amounts
            if inv_line.price_unit and inv_line.quantity:
                amount = inv_line.price_unit * inv_line.quantity
            else:
                amount = 0
            weight = (inv_line.product_id.weight or 0.0) * \
                inv_line.uom_id._compute_quantity(inv_line.quantity, inv_line.product_id.uom_id)
            if not inv_line.product_id.uom_id.category_id:
                supply_units = inv_line.quantity
            else:
                supply_units = inv_line.quantity * inv_line.uom_id.factor
            amounts = entries.setdefault(linekey, (0, 0, 0))
            amounts = (amounts[0] + amount, amounts[1] + weight, amounts[2] + supply_units)
            entries[linekey] = amounts

        numlgn = 0
        for linekey in entries:
            amounts = entries[linekey]
            if round(amounts[0], 0) == 0:
                continue
            numlgn += 1
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
            if dispatchmode:
                self._set_Dim(item, 'EXCNTORI', unicode(linekey.EXCNTORI))
                self._set_Dim(item, 'PARTNERID', unicode(linekey.PARTNERID))

        if numlgn == 0:
            #no datas
            datas.set('action', 'nihil')
        return decl