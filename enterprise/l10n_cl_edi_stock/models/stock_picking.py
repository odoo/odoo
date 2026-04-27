# -*- coding: utf-8 -*-
import base64
import io
import logging
import re

import psycopg2.errors
from lxml import etree
from markupsafe import Markup

from odoo import models, fields, _
from odoo.addons.l10n_cl_edi.models.l10n_cl_edi_util import UnexpectedXMLResponse
from odoo.exceptions import UserError
from odoo.tools import float_repr, html_escape

_logger = logging.getLogger(__name__)

try:
    import pdf417gen
except ImportError:
    pdf417gen = None
    _logger.error('Could not import library pdf417gen')

TAX19_SII_CODE = 14


class Picking(models.Model):
    _name = 'stock.picking'
    _inherit = ['l10n_cl.edi.util', 'stock.picking']

    l10n_cl_delivery_guide_reason = fields.Selection([
            ('1', '1. Operation is sale'),
            ('2', '2. Sales to be made'),
            ('3', '3. Consignments'),
            ('4', '4. Free delivery'),
            ('5', '5. Internal Transfer'),
            ('6', '6. Other not-sale transfers'),
            ('7', '7. Return guide'),
            ('8', '8. Exportation Transfers'),
            ('9', '9. Export Sales')
        ], string='Reason of the Transfer', default='1')

    # Technical field making it possible to have a draft status for entering
    # the starting number for the guia in this company
    l10n_cl_draft_status = fields.Boolean(copy=False)
    # delivery guide is not mandatory for return case
    l10n_cl_is_return = fields.Boolean(compute="_compute_l10n_cl_is_return")
    # Common fields that will go into l10n_cl.edi.util in master (check copy=False as this flag was not in edi util):
    l10n_latam_document_type_id = fields.Many2one('l10n_latam.document.type', string='Document Type',
                                                  readonly=True, copy=False)
    l10n_latam_document_number = fields.Char(string='Delivery Guide Number', copy=False)
    l10n_cl_sii_barcode = fields.Char(
        string='SII Barcode', readonly=True, copy=False,
        help='This XML contains the portion of the DTE XML that should be coded in PDF417 '
             'and printed in the invoice barcode should be present in the printed invoice report to be valid')
    l10n_cl_dte_status = fields.Selection([
        ('not_sent', 'Pending To Be Sent'),
        ('ask_for_status', 'Ask For Status'),
        ('accepted', 'Accepted'),
        ('objected', 'Accepted With Objections'),
        ('rejected', 'Rejected'),
        ('cancelled', 'Cancelled'),
        ('manual', 'Manual'),
    ], string='SII DTE status', copy=False, tracking=True, help="""Status of sending the DTE to the SII:
            - Not sent: the DTE has not been sent to SII but it has created.
            - Ask For Status: The DTE is asking for its status to the SII.
            - Accepted: The DTE has been accepted by SII.
            - Accepted With Objections: The DTE has been accepted with objections by SII.
            - Rejected: The DTE has been rejected by SII.
            - Cancelled: The DTE has been deleted by the user.
            - Manual: The DTE is sent manually, i.e.: the DTE will not be sending manually.""")
    l10n_cl_dte_partner_status = fields.Selection([
        ('not_sent', 'Not Sent'),
        ('sent', 'Sent'),
    ], string='Partner DTE status', copy=False, readonly=True, help="""
            Status of sending the DTE to the partner:
            - Not sent: the DTE has not been sent to the partner but it has sent to SII.
            - Sent: The DTE has been sent to the partner.""")
    l10n_cl_sii_send_file = fields.Many2one('ir.attachment', string='SII Send file', copy=False)
    l10n_cl_dte_file = fields.Many2one('ir.attachment', string='DTE file', copy=False)
    l10n_cl_sii_send_ident = fields.Text(string='SII Send Identification(Track ID)', copy=False, tracking=True)

    _sql_constraints = [
        ('unique_document_number_in_company', 'UNIQUE(l10n_latam_document_number, company_id)',
         'You should have a unique document number within the company. ')]

    def action_cancel(self):
        for record in self.filtered(
                lambda x: x.company_id.country_id == self.env.ref('base.cl') and x.l10n_cl_dte_status):
            # The move cannot be modified once the DTE has been accepted by the SII
            if record.l10n_cl_dte_status == 'accepted':
                raise UserError(_('%s is accepted by SII. It cannot be cancelled.', self.name))
            record.l10n_cl_dte_status = 'cancelled'
        return super().action_cancel()

    def _create_new_sequence(self):
        return self.env['ir.sequence'].sudo().create({
            'name': 'Stock Picking CAF Sequence',
            'code': 'l10n_cl_edi_stock.stock_picking_caf_sequence',
            'padding': 6,
            'company_id': self.company_id.id,
            'number_next': int(self.l10n_latam_document_number) + 1
        })

    def _get_next_document_number(self):
        return self.env['ir.sequence'].next_by_code('l10n_cl_edi_stock.stock_picking_caf_sequence')

    def create_delivery_guide(self):
        self.ensure_one()
        if self.company_id.country_id.code != 'CL' or not self.company_id.l10n_cl_dte_service_provider:
            raise UserError(_("This company has no connection with the SII configured.  "))
        document_type = self.env['l10n_latam.document.type'].search([('code', '=', 52)], limit=1)
        if not document_type:
            raise UserError(_('Document type with code 52 active not found. You can update the module to solve this problem. '))
        self.l10n_latam_document_type_id = document_type
        self._l10n_cl_create_delivery_guide_validation()

        if not self.env['ir.sequence'].search_count([('code', '=', 'l10n_cl_edi_stock.stock_picking_caf_sequence'),
                                                ('company_id', '=', self.company_id.id)], limit=1):
            self.l10n_cl_draft_status = True
            return True
        if not self.l10n_latam_document_number:
            self.l10n_latam_document_number = self._get_next_document_number()
        self.l10n_cl_dte_status = 'not_sent'
        msg_demo = _('DTE has been created in DEMO mode.') if self.company_id.l10n_cl_dte_service_provider == 'SIIDEMO' else _('DTE has been created.')
        self._l10n_cl_create_dte()
        dte_signed, file_name = self._l10n_cl_get_dte_envelope()
        attachment = self.env['ir.attachment'].create({
            'name': 'SII_{}'.format(file_name),
            'res_id': self.id,
            'res_model': self._name,
            'datas': base64.b64encode(dte_signed.encode('ISO-8859-1', 'replace')),
            'type': 'binary',
        })
        self.l10n_cl_sii_send_file = attachment.id
        self.message_post(body=msg_demo, attachment_ids=attachment.ids)
        return self.print_delivery_guide_pdf()

    def _compute_l10n_cl_is_return(self):
        for picking in self:
            if picking.country_code == 'CL':
                picking.l10n_cl_is_return = any(m.origin_returned_move_id for m in picking.move_ids_without_package)
            else:
                picking.l10n_cl_is_return = False

    def _get_effective_date(self):
        self.ensure_one()
        return fields.Date.context_today(self, self.date_done if self.date_done else self.scheduled_date)

    def print_delivery_guide_pdf(self):
        return self.env.ref('l10n_cl_edi_stock.action_delivery_guide_report_pdf').report_action(self)

    def l10n_cl_confirm_draft_delivery_guide(self):
        for record in self:
            if not self.env['ir.sequence'].search_count([('code', '=', 'l10n_cl_edi_stock.stock_picking_caf_sequence'),
                                                   ('company_id', '=', self.company_id.id)], limit=1):
                if not record.l10n_latam_document_number:
                    raise UserError(_('You need to specify a Document Number'))
                self._create_new_sequence()
            record.create_delivery_guide()
            record.l10n_cl_draft_status = False

    def l10n_cl_set_delivery_guide_to_draft(self):
        for record in self:
            record.l10n_cl_draft_status = True
            record.l10n_cl_dte_status = False
            record.l10n_cl_sii_send_file = False

    # DTE creation
    def _l10n_cl_create_dte(self):
        sii_barcode, signed_dte = self._l10n_cl_get_signed_dte()
        self.l10n_cl_sii_barcode = sii_barcode
        dte_attachment = self.env['ir.attachment'].create({
            'name': 'DTE_{}.xml'.format(self.l10n_latam_document_number),
            'res_model': self._name,
            'res_id': self.id,
            'type': 'binary',
            'datas': base64.b64encode(signed_dte.encode('ISO-8859-1', 'replace'))
        })
        self.l10n_cl_dte_file = dte_attachment.id

    # Validation
    def _l10n_cl_create_delivery_guide_validation(self):
        if not self.partner_id:
            raise UserError(_('Please set a Delivery Address as the delivery guide needs one.'))
        if not self.partner_id.l10n_cl_delivery_guide_price:
            raise UserError(_('Please, configure the Delivery Guide Price in the partner.'))
        if self.partner_id._l10n_cl_is_foreign():
            raise UserError(_('Delivery Guide for foreign partner is not implemented yet'))
        if not self.company_id.l10n_cl_company_activity_ids:
            raise UserError(_(
                'There are no activity codes configured in your company. This is mandatory for electronic '
                'delivery guide. Please go to your company and set the correct activity codes (www.sii.cl - Mi SII)'))
        if not self.company_id.l10n_cl_sii_regional_office:
            raise UserError(_(
                'There is no SII Regional Office configured in your company. This is mandatory for electronic '
                'delivery guide. Please go to your company and set the regional office, according to your company '
                'address (www.sii.cl - Mi SII)'))
        if not self.company_id.partner_id.city:
            raise UserError(_(
                'There is no city configured in your partner company. This is mandatory for electronic'
                'delivery guide. Please go to your partner company and set the city.'
            ))
        if not self.company_id.l10n_cl_activity_description:
            raise UserError(_(
                'Your company has not an activity description configured. This is mandatory for electronic '
                'delivery guide. Please go to your company and set the correct one (www.sii.cl - Mi SII)'))
        if not (self.partner_id.l10n_cl_activity_description or self.partner_id.commercial_partner_id.l10n_cl_activity_description):
            raise UserError(_(
                'There is not an activity description configured in the '
                'customer record. This is mandatory for electronic delivery guide for this type of '
                'document. Please go to the partner record and set the activity description'))
        if not self.partner_id.street:
            raise UserError(_(
                'There is no address configured in your customer record. '
                'This is mandatory for electronic delivery guide for this type of document. '
                'Please go to the partner record and set the address'))
        caf_file = self.env['l10n_cl.dte.caf'].sudo().search([
            ('company_id', '=', self.company_id.id), ('status', '=', 'in_use'),
            ('l10n_latam_document_type_id', '=', self.l10n_latam_document_type_id.id)])
        if not caf_file:
            raise UserError(_('CAF file for the document type %s not found. Please, upload a caf file before to '
                              'create the delivery guide', self.l10n_latam_document_type_id.code))

    def _l10n_cl_edi_prepare_values(self):
        move_ids = self.move_ids
        values = {
            'format_vat': self._l10n_cl_format_vat,
            'format_length': self._format_length,
            'format_uom': self._format_uom,
            'time_stamp': self._get_cl_current_strftime(),
            'caf': self.l10n_latam_document_type_id.sudo()._get_caf_file(self.company_id.id,
                                                                  int(self.l10n_latam_document_number)),
            'fe_value': self._get_cl_current_datetime().date(),
            'rr_value': '55555555-5' if self.partner_id._l10n_cl_is_foreign() else self._l10n_cl_format_vat(
                self.partner_id.vat),
            'rsr_value': self._format_length(self.partner_id.name, 40),
            'mnt_value': float_repr(self._l10n_cl_get_tax_amounts()[0]['total_amount'], 0),
            'picking': self,
            'it1_value': self._format_length(move_ids[0].product_id.name, 40) if move_ids else '',
            '__keep_empty_lines': True,
        }
        return values

    def _l10n_cl_get_tax_amounts(self):
        """
        Calculates the totals of the tax amounts on the picking
        :return: totals, retentions, line_amounts
        """
        totals = {
                'vat_amount': 0,
                'subtotal_amount_taxable': 0,
                'subtotal_amount_exempt': 0,
                'vat_percent': False,
                'total_amount': 0,
            }
        retentions = {}
        line_amounts = {}
        guide_price = self.partner_id.l10n_cl_delivery_guide_price
        if guide_price == "none":
            return totals, retentions, line_amounts
        # No support for foreign currencies: fallback on product price
        if guide_price == "sale_order" and (
                not self.sale_id or self.sale_id.currency_id != self.company_id.currency_id):
            guide_price = "product"
        max_vat_perc = 0.0
        move_retentions = self.env['account.tax']
        for move in self.move_ids.filtered(lambda x: x.quantity > 0):
            sale_line = move.sale_line_id
            if guide_price == "product" or not sale_line:
                taxes = move.product_id.taxes_id.filtered(lambda t: t.company_id == self.company_id)
                price = move.product_id.lst_price
                qty = move.quantity
            elif guide_price == "sale_order":
                taxes = sale_line.tax_id
                qty = move.product_uom._compute_quantity(move.quantity, sale_line.product_uom)
                price = sale_line.price_unit * (1 - (sale_line.discount or 0.0) / 100.0)

            tax_res = taxes.compute_all(
                price,
                currency=self.company_id.currency_id,
                quantity=qty,
                partner=self.partner_id
            )
            totals['total_amount'] += tax_res['total_included']

            no_vat_taxes = True
            tax_group_ila = self.env['account.chart.template'].with_company(move.company_id).ref('tax_group_ila', raise_if_not_found=False)
            tax_group_retenciones = self.env['account.chart.template'].with_company(move.company_id).ref('tax_group_retenciones', raise_if_not_found=False)
            for tax_val in tax_res['taxes']:
                tax = self.env['account.tax'].browse(tax_val['id'])
                if tax.l10n_cl_sii_code == TAX19_SII_CODE:
                    no_vat_taxes = False
                    totals['vat_amount'] += tax_val['amount']
                    max_vat_perc = max(max_vat_perc, tax.amount)
                elif tax.tax_group_id.id in [
                    tax_group_ila and tax_group_ila.id,
                    tax_group_retenciones and tax_group_retenciones.id
                ]:
                    retentions.setdefault((tax.l10n_cl_sii_code, tax.amount, tax.tax_group_id.name), 0.0)
                    retentions[(tax.l10n_cl_sii_code, tax.amount, tax.tax_group_id.name)] += tax_val['amount']
                    move_retentions |= tax
            if no_vat_taxes:
                totals['subtotal_amount_exempt'] += tax_res['total_excluded']
            else:
                totals['subtotal_amount_taxable'] += tax_res['total_excluded']

            line_amounts[move] = {
                "value": self.company_id.currency_id.round(tax_res['total_included']),
                'total_amount': self.company_id.currency_id.round(tax_res['total_excluded']),
                "price_unit": self.company_id.currency_id.round(tax_res['total_excluded'] / move.quantity),
                "wh_taxes": move_retentions,
                "exempt": not taxes and tax_res['total_excluded'] != 0.0,
            }
            if guide_price == "sale_order" and sale_line.discount:
                tax_res_disc = taxes.compute_all(
                    sale_line.price_unit,
                    currency=self.company_id.currency_id,
                    quantity=qty,
                    partner=self.partner_id
                )
                line_amounts[move].update({
                    'price_unit': self.company_id.currency_id.round(
                        tax_res_disc['total_excluded'] / move.product_uom_qty),
                    'discount': sale_line.discount,
                    'total_discount': float_repr(self.company_id.currency_id.round(tax_res_disc['total_excluded'] * sale_line.discount / 100), 0),
                    'total_discount_fl': self.company_id.currency_id.round(tax_res_disc['total_excluded'] * sale_line.discount / 100),
                })

        totals['vat_percent'] = max_vat_perc and float_repr(max_vat_perc, 2) or False
        retention_res = []
        for key in retentions:
            retention_res.append({'tax_code': key[0],
                                  'tax_percent': key[1],
                                  'tax_name': key[2],
                                  'tax_amount': self.company_id.currency_id.round(retentions[key])})
        return totals, retention_res, line_amounts

    def _prepare_pdf_values(self):
        amounts, withholdings, total_line_amounts = self._l10n_cl_get_tax_amounts()
        result = {
            'float_repr': float_repr,
            'amounts': amounts,
            'withholdings': withholdings,
            'total_line_amounts': total_line_amounts,
            'has_unit_price': any([l['price_unit'] != 0.0 for l in total_line_amounts.values()]),
            'has_discount': any(l.get('total_discount', '0') != '0' for l in total_line_amounts.values()),
        }
        return result

    def _prepare_dte_values(self):
        folio = int(self.l10n_latam_document_number)
        doc_id_number = 'F{}T{}'.format(folio, self.l10n_latam_document_type_id.code)
        caf_file = self.l10n_latam_document_type_id.sudo()._get_caf_file(self.company_id.id,
                                                                  int(self.l10n_latam_document_number))
        dte_barcode_xml = self._l10n_cl_get_dte_barcode_xml(caf_file)
        amounts, withholdings, total_line_amounts = self._l10n_cl_get_tax_amounts()
        result = {
            # 'move': self,
            'float_repr': float_repr,
            'format_vat': self._l10n_cl_format_vat,
            'get_cl_current_strftime': self._get_cl_current_strftime,
            'format_uom': self._format_uom,
            'format_length': self._format_length,
            'doc_id': doc_id_number,
            'caf': caf_file,
            'dte': dte_barcode_xml['ted'],
            # Specific to the delivery guide:
            'picking': self,
            'amounts': amounts,
            'withholdings': withholdings,
            'total_line_amounts': total_line_amounts,
        }
        return result

    # SII Delivery Guide Buttons
    def l10n_cl_send_dte_to_sii(self, retry_send=True):
        self._l10n_cl_send_dte_to_sii(retry_send=retry_send)

    def l10n_cl_verify_dte_status(self, send_dte_to_partner=True):
        self._l10n_cl_verify_dte_status(send_dte_to_partner=send_dte_to_partner)

    # Cron methods
    def _l10n_cl_ask_dte_status(self):
        for picking in self.search([('l10n_cl_dte_status', '=', 'ask_for_status')]):
            picking.l10n_cl_verify_dte_status(send_dte_to_partner=False)
            self.env.cr.commit()

    # COMMON / DUPLICATED METHODS with account.move
    def _l10n_cl_get_comuna_recep(self):
        if self.partner_id._l10n_cl_is_foreign():
            return self._format_length(self.partner_id.state_id.name or (
                    self.partner_id.commercial_partner_id and self.partner_id.commercial_partner_id.state_id.name) or
                                       'N-A', 20)
        if self.l10n_latam_document_type_id._is_doc_type_voucher():
            return 'N-A'
        return self.partner_id.city or self.partner_id.commercial_partner_id.city or False

    def _l10n_cl_get_sii_reception_status_message(self, sii_response_status):
        """
        Get the value of the code returns by SII once the DTE has been sent to the SII.
        """
        return {
            '0': _('Upload OK'),
            '1': _('Sender Does Not Have Permission To Send'),
            '2': _('File Size Error (Too Big or Too Small)'),
            '3': _('Incomplete File (Size <> Parameter size)'),
            '5': _('Not Authenticated'),
            '6': _('Company Not Authorized to Send Files'),
            '7': _('Invalid Schema'),
            '8': _('Document Signature'),
            '9': _('System Locked'),
            'Otro': _('Internal Error'),
        }.get(sii_response_status, 'Otro')

    def _l10n_cl_get_dte_barcode_xml(self, caf_file):
        """
        This method create the "stamp" (timbre). Is the auto-contained information inside the pdf417 barcode, which
        consists of a reduced xml version of the invoice, containing: issuer, recipient, folio and the first line
        of the invoice, etc.
        :return: xml that goes embedded inside the pdf417 code
        """
        dd = self.env['ir.qweb']._render('l10n_cl_edi_stock.dd_template', self._l10n_cl_edi_prepare_values())
        ted = self.env['ir.qweb']._render('l10n_cl_edi.ted_template', {
            'dd': dd,
            'frmt': self.env['certificate.key']._sign_with_key(
                re.sub(b'\n\\s*', b'', dd.encode('ISO-8859-1', 'replace')),
                base64.b64encode(caf_file.findtext('RSASK').encode('utf-8')),
                hashing_algorithm='sha1',
                formatting='base64',
            ).decode(),
            'stamp': self._get_cl_current_strftime()
        })
        return {
            'ted': Markup(re.sub(r'\n\s*$', '', ted, flags=re.MULTILINE)),
            'barcode': etree.tostring(etree.fromstring(re.sub(
                r'<TmstFirma>.*</TmstFirma>', '', ted.replace('&', '&amp;')),
                parser=etree.XMLParser(remove_blank_text=True)))
        }

    def _pdf417_barcode(self, barcode_data):
        #  This method creates the graphic representation of the barcode
        barcode_file = io.BytesIO()
        if pdf417gen is None:
            return False
        bc = pdf417gen.encode(barcode_data, security_level=5, columns=13)
        image = pdf417gen.render_image(bc, padding=15, scale=1)
        image.save(barcode_file, 'PNG')
        data = barcode_file.getvalue()
        return base64.b64encode(data)

    def _get_dte_template(self):
        return self.env.ref('l10n_cl_edi_stock.dte_template')

    def _l10n_cl_get_signed_dte(self):
        folio = int(self.l10n_latam_document_number)
        doc_id_number = 'F{}T{}'.format(folio, self.l10n_latam_document_type_id.code)
        caf_file = self.l10n_latam_document_type_id.sudo()._get_caf_file(self.company_id.id,
                                                                  int(self.l10n_latam_document_number))
        dte_barcode_xml = self._l10n_cl_get_dte_barcode_xml(caf_file)
        dte = self.env['ir.qweb']._render(self._get_dte_template().id, self._prepare_dte_values())
        digital_signature_sudo = self.company_id.sudo()._get_digital_signature(user_id=self.env.user.id)
        signed_dte = self._sign_full_xml(
            dte, digital_signature_sudo, doc_id_number, 'doc', self.l10n_latam_document_type_id._is_doc_type_voucher())

        return dte_barcode_xml['barcode'], signed_dte

    def _l10n_cl_get_dte_envelope(self, receiver_rut='60803000-K'):
        file_name = 'F{}T{}.xml'.format(self.l10n_latam_document_number, self.l10n_latam_document_type_id.code)
        digital_signature_sudo = self.company_id.sudo()._get_digital_signature(user_id=self.env.user.id)
        # Guia is always DTE
        dte = self.l10n_cl_dte_file.raw.decode('ISO-8859-1')
        dte = Markup(dte.replace('<?xml version="1.0" encoding="ISO-8859-1" ?>', ''))
        dte_rendered = self.env['ir.qweb']._render('l10n_cl_edi.envio_dte', {
            'move': self, # Only needed for the name of the document type
            'RutEmisor': self._l10n_cl_format_vat(self.company_id.vat),
            'RutEnvia': digital_signature_sudo.subject_serial_number,
            'RutReceptor': receiver_rut,
            'FchResol': self.company_id.l10n_cl_dte_resolution_date,
            'NroResol': self.company_id.l10n_cl_dte_resolution_number,
            'TmstFirmaEnv': self._get_cl_current_strftime(),
            'dte': dte,
            '__keep_empty_lines': True,
        })
        dte_signed = self._sign_full_xml(
            dte_rendered, digital_signature_sudo, 'SetDoc',
            self.l10n_latam_document_type_id._is_doc_type_voucher() and 'bol' or 'env',
            self.l10n_latam_document_type_id._is_doc_type_voucher()
        )
        return dte_signed, file_name

    # DTE creation

    def _l10n_cl_create_partner_dte(self):
        dte_signed, file_name = self._l10n_cl_get_dte_envelope(self.partner_id.vat)
        dte_partner_attachment = self.env['ir.attachment'].create({
            'name': file_name,
            'res_model': self._name,
            'res_id': self.id,
            'type': 'binary',
            'datas': base64.b64encode(dte_signed.encode('ISO-8859-1', 'replace'))
        })
        self.with_context(no_new_invoice=True).message_post(
            body=_('Partner DTE has been generated'),
            attachment_ids=[dte_partner_attachment.id])
        return dte_partner_attachment

    # DTE sending

    def _l10n_cl_send_dte_to_partner(self):
        # We need a DTE with the partner vat as RutReceptor to be sent to the partner
        dte_partner_attachment = self._l10n_cl_create_partner_dte()
        self.env.ref('l10n_cl_edi_stock.l10n_cl_edi_email_template_picking').send_mail(
            self.id, email_values={'attachment_ids': [dte_partner_attachment.id]})
        self.l10n_cl_dte_partner_status = 'sent'
        self.message_post(body=_('DTE has been sent to the partner'))

    # SII Customer Invoice Buttons

    def _l10n_cl_send_dte_to_sii(self, retry_send=True):
        """
        Send the DTE to the SII. It will be
        """
        try:
            with self.env.cr.savepoint(flush=False):
                self.env.cr.execute(f'SELECT 1 FROM {self._table} WHERE id IN %s FOR UPDATE NOWAIT', [tuple(self.ids)])
        except psycopg2.errors.LockNotAvailable:
            if not self.env.context.get('cron_skip_connection_errs'):
                raise UserError(_('This electronic document is being processed already.')) from None
            return
        # To avoid double send on double-click
        if self.l10n_cl_dte_status != "not_sent":
            return None
        digital_signature_sudo = self.company_id.sudo()._get_digital_signature(user_id=self.env.user.id)
        if self.company_id.l10n_cl_dte_service_provider == 'SIIDEMO':
            self.message_post(body=_('This DTE has been generated in DEMO Mode. It is considered as accepted and '
                                     'it won\'t be sent to SII.'))
            self.l10n_cl_dte_status = 'accepted'
            return None
        params = {
            'rutSender': digital_signature_sudo.subject_serial_number[:-2],
            'dvSender': digital_signature_sudo.subject_serial_number[-1],
            'rutCompany': self._l10n_cl_format_vat(self.company_id.vat)[:-2],
            'dvCompany': self._l10n_cl_format_vat(self.company_id.vat)[-1],
            'archivo': (
                self.l10n_cl_sii_send_file.name,
                base64.b64decode(self.l10n_cl_sii_send_file.datas),
                'application/xml'),
        }
        response = self._send_xml_to_sii(
            self.company_id.l10n_cl_dte_service_provider,
            self.company_id.website,
            params,
            digital_signature_sudo
        )
        if not response:
            return None

        response_parsed = etree.fromstring(response)
        self.l10n_cl_sii_send_ident = response_parsed.findtext('TRACKID')
        sii_response_status = response_parsed.findtext('STATUS')
        if sii_response_status == '5':
            digital_signature_sudo.last_token = False
            _logger.warning('The response status is %s. Clearing the token.',
                          self._l10n_cl_get_sii_reception_status_message(sii_response_status))
            if retry_send:
                _logger.info('Retrying send DTE to SII')
                self.l10n_cl_send_dte_to_sii(retry_send=False)

            # cleans the token and keeps the l10n_cl_dte_status until new attempt to connect
            # would like to resend from here, because we cannot wait till tomorrow to attempt
            # a new send
        else:
            self.l10n_cl_dte_status = 'ask_for_status' if sii_response_status == '0' else 'rejected'
        self.message_post(body=_('DTE has been sent to SII with response: %s.',
                               self._l10n_cl_get_sii_reception_status_message(sii_response_status)))

    def _l10n_cl_verify_dte_status(self, send_dte_to_partner=True):
        digital_signature_sudo = self.company_id.sudo()._get_digital_signature(user_id=self.env.user.id)
        response = self._get_send_status(
            self.company_id.l10n_cl_dte_service_provider,
            self.l10n_cl_sii_send_ident,
            self._l10n_cl_format_vat(self.company_id.vat),
            digital_signature_sudo)
        if not response:
            self.l10n_cl_dte_status = 'ask_for_status'
            digital_signature_sudo.last_token = False
            return None

        response_parsed = etree.fromstring(response.encode('utf-8'))

        if response_parsed.findtext('{http://www.sii.cl/XMLSchema}RESP_HDR/ESTADO') in ['001', '002', '003']:
            digital_signature_sudo.last_token = False
            _logger.error('Token is invalid.')
            return

        try:
            self.l10n_cl_dte_status = self._analyze_sii_result(response_parsed)
        except UnexpectedXMLResponse:
            # The assumption here is that the unexpected input is intermittent,
            # so we'll retry later. If the same input appears regularly, it should
            # be handled properly in _analyze_sii_result.
            _logger.error("Unexpected XML response:\n%s", response)
            return

        if self.l10n_cl_dte_status in ['accepted', 'objected']:
            self.l10n_cl_dte_partner_status = 'not_sent'
            if send_dte_to_partner:
                self._l10n_cl_send_dte_to_partner()

        self.message_post(
            body=_('Asking for DTE status with response:') +
                 Markup('<br /><li><b>ESTADO</b>: %s</li><li><b>GLOSA</b>: %s</li><li><b>NUM_ATENCION</b>: %s</li>') % (
                     response_parsed.findtext('{http://www.sii.cl/XMLSchema}RESP_HDR/ESTADO'),
                     response_parsed.findtext('{http://www.sii.cl/XMLSchema}RESP_HDR/GLOSA'),
                     response_parsed.findtext('{http://www.sii.cl/XMLSchema}RESP_HDR/NUM_ATENCION')))
