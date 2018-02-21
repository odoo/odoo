# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import base64
from xml.etree import ElementTree as ET
from collections import namedtuple

from odoo import api, exceptions, fields, models, _
from odoo.tools.pycompat import text_type

INTRASTAT_XMLNS = 'http://www.onegate.eu/2010-01-01'


class XmlDeclaration(models.TransientModel):
    """
    Intrastat XML Declaration
    """
    _name = "l10n_be_intrastat_xml.xml_decl"
    _description = 'Intrastat XML Declaration'

    def _default_get_month(self):
        return fields.Date.from_string(fields.Date.context_today(self)).strftime('%m')

    def _default_get_year(self):
        return fields.Date.from_string(fields.Date.context_today(self)).strftime('%Y')

    name = fields.Char(string='File Name', default='intrastat.xml')
    month = fields.Selection([('01', 'January'), ('02', 'February'), ('03', 'March'),
                               ('04', 'April'), ('05', 'May'), ('06', 'June'), ('07', 'July'),
                               ('08', 'August'), ('09', 'September'), ('10', 'October'),
                               ('11', 'November'), ('12', 'December')], string='Month', required=True, default=_default_get_month)
    year = fields.Char(size=4, required=True, default=_default_get_year)
    company_id = fields.Many2one('res.company', string='Company', required=True, default=lambda self: self.env.user.company_id)
    arrivals = fields.Selection([('be-exempt', 'Exempt'),
                                  ('be-standard', 'Standard'),
                                  ('be-extended', 'Extended')],
                                 required=True, default='be-standard')
    dispatches = fields.Selection([('be-exempt', 'Exempt'),
                                  ('be-standard', 'Standard'),
                                  ('be-extended', 'Extended')],
                                   required=True, default='be-standard')
    file_save = fields.Binary(string='Intrastat Report File', readonly=True)
    state = fields.Selection([('draft', 'Draft'), ('download', 'Download')], default='draft')

    @api.model
    def _company_warning(self, translated_msg):
        """ Raise a error with custom message, asking user to configure company settings """
        raise exceptions.RedirectWarning(
            translated_msg, self.env.ref('base.action_res_company_form').id, _('Go to company configuration screen'))

    @api.multi
    def create_xml(self):
        """Creates xml that is to be exported and sent to estate for partner vat intra.
        :return: Value for next action.
        :rtype: dict
        """
        self.ensure_one()
        company = self.company_id
        if not (company.partner_id and company.partner_id.country_id and
                company.partner_id.country_id.id):
            self._company_warning(_('The country of your company is not set, '
                  'please make sure to configure it first.'))
        if not company.company_registry:
            self._company_warning(_('The registry number of your company is not set, '
                  'please make sure to configure it first.'))
        if len(self.year) != 4:
            raise exceptions.Warning(_('Year must be 4 digits number (YYYY)'))

        #Create root declaration
        decl = ET.Element('DeclarationReport')
        decl.set('xmlns', INTRASTAT_XMLNS)

        #Add Administration elements
        admin = ET.SubElement(decl, 'Administration')
        fromtag = ET.SubElement(admin, 'From')
        fromtag.text = company.company_registry
        fromtag.set('declarerType', 'KBO')
        ET.SubElement(admin, 'To').text = "NBB"
        ET.SubElement(admin, 'Domain').text = "SXX"
        if self.arrivals == 'be-standard':
            decl.append(self.sudo()._get_lines(dispatchmode=False, extendedmode=False))
        elif self.arrivals == 'be-extended':
            decl.append(self.sudo()._get_lines(dispatchmode=False, extendedmode=True))
        if self.dispatches == 'be-standard':
            decl.append(self.sudo()._get_lines(dispatchmode=True, extendedmode=False))
        elif self.dispatches == 'be-extended':
            decl.append(self.sudo()._get_lines(dispatchmode=True, extendedmode=True))

        #Get xml string with declaration
        data_file = ET.tostring(decl, encoding='UTF-8', method='xml')

        #change state of the wizard
        self.write({'name': 'intrastat_%s%s.xml' % (self.year, self.month),
                    'file_save': base64.encodestring(data_file),
                    'state': 'download'})
        return {
            'name': _('Save'),
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'l10n_be_intrastat_xml.xml_decl',
            'type': 'ir.actions.act_window',
            'target': 'new',
            'res_id': self.id,
        }

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
                                   'EXGO', 'EXTPC', 'EXDELTRM'])
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
                excnt = inv_line.invoice_id.partner_id.country_id.code

            #Check region
            #If purchase, comes from purchase order, linked to a location,
            #which is linked to the warehouse
            #if sales, the sales order is linked to the warehouse
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
            linekey = intrastatkey(EXTRF=declcode, EXCNT=excnt,
                                   EXTTA=extta, EXREG=exreg, EXGO=exgo,
                                   EXTPC=extpc, EXDELTRM=exdeltrm)
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
            self._set_Dim(item, 'EXSEQCODE', text_type(numlgn))
            self._set_Dim(item, 'EXTRF', text_type(linekey.EXTRF))
            self._set_Dim(item, 'EXCNT', text_type(linekey.EXCNT))
            self._set_Dim(item, 'EXTTA', text_type(linekey.EXTTA))
            self._set_Dim(item, 'EXREG', text_type(linekey.EXREG))
            self._set_Dim(item, 'EXTGO', text_type(linekey.EXGO))
            if extendedmode:
                self._set_Dim(item, 'EXTPC', text_type(linekey.EXTPC))
                self._set_Dim(item, 'EXDELTRM', text_type(linekey.EXDELTRM))
            self._set_Dim(item, 'EXTXVAL', text_type(round(amounts[0], 0)).replace(".", ","))
            self._set_Dim(item, 'EXWEIGHT', text_type(round(amounts[1], 0)).replace(".", ","))
            self._set_Dim(item, 'EXUNITS', text_type(round(amounts[2], 0)).replace(".", ","))

        if numlgn == 0:
            #no datas
            datas.set('action', 'nihil')
        return decl

    def _set_Dim(self, item, prop, value):
        dim = ET.SubElement(item, 'Dim')
        dim.set('prop', prop)
        dim.text = value

    def _is_situation_triangular(self, company, po_line=False, so_line=False):
        # Ignoring what is purchased and sold by us with a dropshipping route
        # outside of our country, or completely within it
        # https://www.nbb.be/doc/dq/f_pdf_ex/intra2017fr.pdf (§ 4.x)
        dropship_pick_type = self.env.ref('stock_dropshipping.picking_type_dropship', raise_if_not_found=False)
        if not dropship_pick_type:
            return False
        stock_move_domain = [('picking_type_id', '=', dropship_pick_type.id)]

        if po_line:
            stock_move_domain.append(('purchase_line_id', '=', po_line.id))
        if so_line:
            stock_move_domain.append(('procurement_id.sale_line_id', '=', so_line.id))

        stock_move = self.env['stock.move'].search(stock_move_domain, limit=1)
        return stock_move and (
            (stock_move.partner_id.country_id.code != company.country_id.code and
                stock_move.picking_partner_id.country_id.code != company.country_id.code) or
            (stock_move.partner_id.country_id.code == company.country_id.code and
                stock_move.picking_partner_id.country_id.code == company.country_id.code))
