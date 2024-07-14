# -*- coding: utf-8 -*-
from collections import defaultdict
from datetime import datetime
import logging
from lxml import etree
from pytz import timezone
import re
from werkzeug.urls import url_quote_plus

from odoo import api, fields, models, Command, _
from odoo.addons.l10n_mx_edi.models.l10n_mx_edi_document import (
    CANCELLATION_REASON_SELECTION,
    CANCELLATION_REASON_DESCRIPTION,
    CFDI_CODE_TO_TAX_TYPE,
    CFDI_DATE_FORMAT,
    USAGE_SELECTION,
)
from odoo.exceptions import ValidationError, UserError
from odoo.tools import frozendict
from odoo.tools.float_utils import float_round
from odoo.tools.sql import column_exists, create_column
from odoo.addons.base.models.ir_qweb import keep_query

_logger = logging.getLogger(__name__)


class AccountMove(models.Model):
    _inherit = 'account.move'

    # ==== CFDI flow fields ====

    l10n_mx_edi_is_cfdi_needed = fields.Boolean(
        compute='_compute_l10n_mx_edi_is_cfdi_needed',
        store=True,
    )
    # The CFDI documents displayed on the invoice.
    # This is a many2many because a payment could pay multiple invoices.
    l10n_mx_edi_invoice_document_ids = fields.Many2many(
        comodel_name='l10n_mx_edi.document',
        relation='l10n_mx_edi_invoice_document_ids_rel',
        column1='invoice_id',
        column2='document_id',
        copy=False,
        readonly=True,
    )
    # The CFDI documents displayed on the payment.
    l10n_mx_edi_payment_document_ids = fields.One2many(
        comodel_name='l10n_mx_edi.document',
        inverse_name='move_id',
        copy=False,
        readonly=True,
    )
    # The CFDI documents for the view.
    l10n_mx_edi_document_ids = fields.One2many(
        comodel_name='l10n_mx_edi.document',
        compute='_compute_l10n_mx_edi_document_ids',
    )
    l10n_mx_edi_cfdi_state = fields.Selection(
        string="CFDI status",
        selection=[
            ('sent', 'Signed'),
            ('cancel_requested', 'Cancel Requested'),
            ('cancel', 'Cancelled'),
            ('received', 'Received'),
            ('global_sent', 'Signed Global'),
            ('global_cancel', 'Cancelled Global'),
        ],
        store=True,
        copy=False,
        tracking=True,
        compute="_compute_l10n_mx_edi_cfdi_state_and_attachment",
    )
    l10n_mx_edi_cfdi_sat_state = fields.Selection(
        string="SAT status",
        selection=[
            ('valid', "Validated"),
            ('cancelled', "Cancelled"),
            ('not_found', "Not Found"),
            ('not_defined', "Not Defined"),
            ('error', "Error"),
        ],
        store=True,
        copy=False,
        tracking=True,
        compute="_compute_l10n_mx_edi_cfdi_state_and_attachment",
    )
    l10n_mx_edi_cfdi_attachment_id = fields.Many2one(
        comodel_name='ir.attachment',
        string="CFDI",
        store=True,
        copy=False,
        index=True,
        compute='_compute_l10n_mx_edi_cfdi_state_and_attachment',
    )
    # Technical field indicating if the "Update Payments" button needs to be displayed on invoice view.
    l10n_mx_edi_update_payments_needed = fields.Boolean(compute='_compute_l10n_mx_edi_update_payments_needed')
    # Technical field indicating if the "Force PUE" button needs to be displayed on payment view.
    l10n_mx_edi_force_pue_payment_needed = fields.Boolean(compute='_compute_l10n_mx_edi_force_pue_payment_needed')
    # Technical field indicating if the "Update SAT" button needs to be displayed on invoice/payment view.
    l10n_mx_edi_update_sat_needed = fields.Boolean(compute='_compute_l10n_mx_edi_update_sat_needed')
    l10n_mx_edi_post_time = fields.Datetime(
        string="Posted Time",
        readonly=True,
        copy=False,
        help="Keep empty to use the current México central time",
    )
    l10n_mx_edi_usage = fields.Selection(
        selection=USAGE_SELECTION,
        string="Usage",
        readonly=False,
        store=True,
        compute='_compute_l10n_mx_edi_usage',
        tracking=True,
        help="Used in CFDI to express the key to the usage that will gives the receiver to this invoice. This "
             "value is defined by the customer.\nNote: It is not cause for cancellation if the key set is not the usage "
             "that will give the receiver of the document.",
    )
    l10n_mx_edi_cfdi_origin = fields.Char(
        string="CFDI Origin",
        copy=False,
        help="In some cases like payments, credit notes, debit notes, invoices re-signed or invoices that are redone "
             "due to payment in advance will need this field filled, the format is:\n"
             "Origin Type|UUID1, UUID2, ...., UUIDn.\n"
             "Where the origin type could be:\n"
             "- 01: Nota de crédito\n"
             "- 02: Nota de débito de los documentos relacionados\n"
             "- 03: Devolución de mercancía sobre facturas o traslados previos\n"
             "- 04: Sustitución de los CFDI previos\n"
             "- 05: Traslados de mercancias facturados previamente\n"
             "- 06: Factura generada por los traslados previos\n"
             "- 07: CFDI por aplicación de anticipo",
    )
    # When cancelling an invoice, the user needs to provide a valid reason to do so to the SAT.
    l10n_mx_edi_invoice_cancellation_reason = fields.Selection(
        selection=CANCELLATION_REASON_SELECTION,
        string="Cancellation Reason",
        compute='_compute_l10n_mx_edi_cfdi_state_and_attachment',
        store=True,
        help=CANCELLATION_REASON_DESCRIPTION,
    )
    # Indicate the journal entry substituting the current cancelled one.
    # In other words, this is the reason why the current journal entry is cancelled.
    l10n_mx_edi_cfdi_cancel_id = fields.Many2one(
        comodel_name='account.move',
        string="Substituted By",
        compute='_compute_l10n_mx_edi_cfdi_cancel_id',
        index='btree_not_null',
    )

    # ==== CFDI certificate fields ====
    l10n_mx_edi_certificate_id = fields.Many2one(
        comodel_name='l10n_mx_edi.certificate',
        string="Source Certificate")
    l10n_mx_edi_cer_source = fields.Char(
        string='Certificate Source',
        help="Used in CFDI like attribute derived from the exception of certificates of Origin of the "
             "Free Trade Agreements that Mexico has celebrated with several countries. If it has a value, it will "
             "indicate that it serves as certificate of origin and this value will be set in the CFDI node "
             "'NumCertificadoOrigen'.")

    # ==== CFDI attachment fields ====
    l10n_mx_edi_cfdi_uuid = fields.Char(
        string="Fiscal Folio",
        compute='_compute_l10n_mx_edi_cfdi_uuid',
        copy=False,
        store=True,
        tracking=True,
        index='btree_not_null',
        help="Folio in electronic invoice, is returned by SAT when send to stamp.",
    )
    l10n_mx_edi_cfdi_supplier_rfc = fields.Char(
        string="Supplier RFC",
        compute='_compute_cfdi_values',
        help="The supplier tax identification number.",
    )
    l10n_mx_edi_cfdi_customer_rfc = fields.Char(
        string="Customer RFC",
        compute='_compute_cfdi_values',
        help="The customer tax identification number.",
    )
    l10n_mx_edi_cfdi_amount = fields.Monetary(
        string="Total Amount",
        compute='_compute_cfdi_values',
        help="The total amount reported on the cfdi.",
    )

    # ==== Other fields ====
    l10n_mx_edi_payment_method_id = fields.Many2one(
        comodel_name='l10n_mx_edi.payment.method',
        string="Payment Way",
        compute='_compute_l10n_mx_edi_payment_method_id',
        store=True,
        readonly=False,
        help="Indicates the way the invoice was/will be paid, where the options could be: "
             "Cash, Nominal Check, Credit Card, etc. Leave empty if unkown and the XML will show 'Unidentified'.",
    )
    # Indicate what kind of payment is expected to pay the current invoice.
    # PUE is for a quick payment close to the invoice date paying completely the invoice.
    # In that case, by default, you don't need to sent the payment to the SAT.
    # PPD means you have either a delay, either multiple partial payments to do.
    # In that case, the payment(s) must be sent to the SAT.
    l10n_mx_edi_payment_policy = fields.Selection(
        string="Payment Policy",
        selection=[('PPD', 'PPD'), ('PUE', 'PUE')],
        compute='_compute_l10n_mx_edi_payment_policy',
    )
    # Indicate if you send the invoice to the SAT using 'Publico En General' meaning
    # the customer is unknown by the SAT. This is mainly used when the customer doesn't have
    # a VAT number registered to the SAT.
    l10n_mx_edi_cfdi_to_public = fields.Boolean(
        string="CFDI to public",
        compute='_compute_l10n_mx_edi_cfdi_to_public',
        store=True,
        readonly=False,
        help="Send the CFDI with recipient 'publico en general'",
    )

    def _auto_init(self):
        """
        Create compute stored field l10n_mx_edi_cfdi_request
        here to avoid MemoryError on large databases.
        """
        if not column_exists(self.env.cr, 'account_move', 'l10n_mx_edi_payment_method_id'):
            create_column(self.env.cr, 'account_move', 'l10n_mx_edi_payment_method_id', 'integer')
        return super()._auto_init()

    # -------------------------------------------------------------------------
    # HELPERS
    # -------------------------------------------------------------------------

    def _l10n_mx_edi_is_cfdi_payment(self):
        """ Helper to know if the current account.move is a payment or not.

        :return: True if the account.move is a payment, False otherwise.
        """
        self.ensure_one()
        return self.payment_id or self.statement_line_id

    def _l10n_mx_edi_cfdi_invoice_append_addenda(self, cfdi, addenda):
        ''' Append an additional block to the signed CFDI passed as parameter.
        :param move:    The account.move record.
        :param cfdi:    The invoice's CFDI as a string.
        :param addenda: (ir.ui.view) The addenda to add as a string.
        :return cfdi:   The cfdi including the addenda.
        '''
        self.ensure_one()
        addenda_values = {'record': self, 'cfdi': cfdi}

        addenda = self.env['ir.qweb']._render(addenda.id, values=addenda_values).strip()
        if not addenda:
            return cfdi

        cfdi_node = etree.fromstring(cfdi)
        addenda_node = etree.fromstring(addenda)
        version = cfdi_node.get('Version')

        # Add a root node Addenda if not specified explicitly by the user.
        if addenda_node.tag != '{http://www.sat.gob.mx/cfd/%s}Addenda' % version[0]:
            node = etree.Element(etree.QName('http://www.sat.gob.mx/cfd/%s' % version[0], 'Addenda'))
            node.append(addenda_node)
            addenda_node = node

        cfdi_node.append(addenda_node)
        return etree.tostring(cfdi_node, pretty_print=True, xml_declaration=True, encoding='UTF-8')

    def _l10n_mx_edi_cfdi_amount_to_text(self):
        """Method to transform a float amount to text words
        E.g. 100 - ONE HUNDRED
        :returns: Amount transformed to words mexican format for invoices
        :rtype: str
        """
        self.ensure_one()

        currency_name = self.currency_id.name.upper()

        # M.N. = Moneda Nacional (National Currency)
        # M.E. = Moneda Extranjera (Foreign Currency)
        currency_type = 'M.N' if currency_name == 'MXN' else 'M.E.'

        # Split integer and decimal part
        amount_i, amount_d = divmod(self.amount_total, 1)
        amount_d = round(amount_d, 2)
        amount_d = int(round(amount_d * 100, 2))

        words = self.currency_id.with_context(lang=self.partner_id.lang or 'es_ES').amount_to_text(amount_i).upper()
        return '%(words)s %(amount_d)02d/100 %(currency_type)s' % {
            'words': words,
            'amount_d': amount_d,
            'currency_type': currency_type,
        }

    def _l10n_mx_edi_check_invoices_for_global_invoice(self, origin=None):
        """ Ensure the current records are eligible for the creation of a global invoice.

        :param origin: The origin of the GI when cancelling an existing one.
        """
        failed_invoices = self.filtered(lambda x: x.state != 'posted')
        if failed_invoices:
            invoices_str = ", ".join(failed_invoices.mapped('name'))
            raise UserError(_("Invoices %s are not posted.", invoices_str))
        if len(self.company_id) != 1 or len(self.journal_id) != 1:
            raise UserError(_("You can only process invoices sharing the same company and journal."))

        refunds = self.reversal_move_id
        invoices = self | refunds
        failed_invoices = invoices.filtered(lambda x: (
            (
                not origin
                and (
                    not x.l10n_mx_edi_is_cfdi_needed
                    or x.l10n_mx_edi_cfdi_state in ('sent', 'global_sent')
                )
            )
            or (x.move_type == 'out_refund' and x.reversed_entry_id not in self)
        ))
        if failed_invoices:
            invoices_str = ", ".join(failed_invoices.mapped('name'))
            raise UserError(_("Invoices %s are already sent or not eligible for CFDI.", invoices_str))
        return invoices

    @api.model
    def _l10n_mx_edi_write_cfdi_origin(self, code, uuids):
        ''' Format the code and uuids passed as parameter in order to fill the l10n_mx_edi_cfdi_origin field.
        The code corresponds to the following types:
            - 01: Nota de crédito
            - 02: Nota de débito de los documentos relacionados
            - 03: Devolución de mercancía sobre facturas o traslados previos
            - 04: Sustitución de los CFDI previos
            - 05: Traslados de mercancias facturados previamente
            - 06: Factura generada por los traslados previos
            - 07: CFDI por aplicación de anticipo

        The generated string must match the following template:
        <code>|<uuid1>,<uuid2>,...,<uuidn>

        :param code:    A valid code as a string between 01 and 07.
        :param uuids:   A list of uuids returned by the government.
        :return:        A valid string to be put inside the l10n_mx_edi_cfdi_origin field.
        '''
        return '%s|%s' % (code, ','.join(uuids))

    def _l10n_mx_edi_get_extra_common_report_values(self):
        self.ensure_one()
        cfdi_infos = self.env['l10n_mx_edi.document']._decode_cfdi_attachment(self.l10n_mx_edi_cfdi_attachment_id.raw)
        if not cfdi_infos:
            return {}

        barcode_value_params = keep_query(
            id=cfdi_infos['uuid'],
            re=cfdi_infos['supplier_rfc'],
            rr=cfdi_infos['customer_rfc'],
            tt=cfdi_infos['amount_total'],
        )
        barcode_sello = url_quote_plus(cfdi_infos['sello'][-8:], safe='=/').replace('%2B', '+')
        barcode_value = url_quote_plus(f'https://verificacfdi.facturaelectronica.sat.gob.mx/default.aspx?{barcode_value_params}&fe={barcode_sello}')
        barcode_src = f'/report/barcode/?barcode_type=QR&value={barcode_value}&width=180&height=180'

        return {
            **cfdi_infos,
            'barcode_src': barcode_src,
        }

    def _l10n_mx_edi_get_extra_invoice_report_values(self):
        """ Collect extra values used to render the invoice PDF report containing CFDI information.

        :return: A python dictionary.
        """
        self.ensure_one()
        cfdi_infos = self._l10n_mx_edi_get_extra_common_report_values()
        if not cfdi_infos:
            return cfdi_infos

        payment_way = cfdi_infos['cfdi_node'].attrib.get('FormaPago')
        if payment_way:
            payment_method = self.env['l10n_mx_edi.payment.method'].search([('code', '=', payment_way)])
            cfdi_infos['payment_way'] = f'{payment_way} - {payment_method.name}'

        return cfdi_infos

    def _l10n_mx_edi_get_extra_payment_report_values(self):
        """ Collect extra values used to render the payment PDF report containing CFDI information.

        :return: A python dictionary.
        """
        self.ensure_one()
        cfdi_infos = self._l10n_mx_edi_get_extra_common_report_values()
        if not cfdi_infos:
            return cfdi_infos

        node = cfdi_infos['cfdi_node'].xpath("//*[local-name()='Pago']")[0]
        payment_info = cfdi_infos['payment_info'] = {}
        payment_info['from_account_vat'] = node.get('RfcEmisorCtaOrd')
        payment_info['from_account_name'] = node.get('NomBancoOrdExt')
        payment_info['from_account_number'] = node.get('CtaOrdenante')
        payment_info['to_account_vat'] = node.get('RfcEmisorCtaBen')
        payment_info['to_account_number'] = node.get('CtaBeneficiario')

        related_invoices = cfdi_infos['invoices'] = []
        uuids = []
        for node in cfdi_infos['cfdi_node'].xpath("//*[local-name()='DoctoRelacionado']"):
            uuids.append(node.attrib['IdDocumento'])
            related_invoices.append({
                'uuid': node.attrib['IdDocumento'],
                'partiality': node.attrib['NumParcialidad'],
                'previous_balance': float(node.attrib['ImpSaldoAnt']),
                'amount_paid': float(node.attrib['ImpPagado']),
                'balance': float(node.attrib['ImpSaldoInsoluto']),
                'currency': node.attrib['MonedaDR'],
            })
        invoices = self.env['account.move'].search([('l10n_mx_edi_cfdi_uuid', 'in', uuids)])
        invoices_map = {x.l10n_mx_edi_cfdi_uuid: x for x in invoices}
        for invoice_values in related_invoices:
            invoice_values['invoice'] = invoices_map.get(invoice_values['uuid'], self.env['account.move'])

        return cfdi_infos

    def _l10n_mx_edi_get_refund_original_invoices(self):
        """ Get the related invoices for the current refunds.

        :return: The refunded invoices.
        """
        origin_uuids = set()
        for move in self.filtered(lambda x: x.move_type == 'out_refund'):
            cfdi_values = {}
            self.env['l10n_mx_edi.document']._add_document_origin_cfdi_values(cfdi_values, move.l10n_mx_edi_cfdi_origin)
            if cfdi_values['tipo_relacion'] in ('01', '03'):
                for uuid in cfdi_values['cfdi_relationado_list']:
                    origin_uuids.add(uuid)
        if origin_uuids:
            return self.env['account.move'].search([('l10n_mx_edi_cfdi_uuid', 'in', list(origin_uuids))])
        return self.env['account.move']

    # -------------------------------------------------------------------------
    # COMPUTE METHODS
    # -------------------------------------------------------------------------

    @api.depends('l10n_mx_edi_cfdi_state', 'l10n_mx_edi_cfdi_cancel_id')
    def _compute_need_cancel_request(self):
        # EXTENDS 'account'
        super()._compute_need_cancel_request()

    @api.depends('country_code')
    def _compute_amount_total_words(self):
        # EXTENDS 'account'
        super()._compute_amount_total_words()
        for move in self:
            if move.country_code == 'MX':
                move.amount_total_words = move._l10n_mx_edi_cfdi_amount_to_text()

    @api.depends('move_type', 'company_currency_id', 'payment_id', 'statement_line_id')
    def _compute_l10n_mx_edi_is_cfdi_needed(self):
        """ Check whatever or not the CFDI is needed on this invoice.
        """
        for move in self:
            move.l10n_mx_edi_is_cfdi_needed = \
                move.country_code == 'MX' \
                and move.company_currency_id.name == 'MXN' \
                and (move.move_type in ('out_invoice', 'out_refund') or move._l10n_mx_edi_is_cfdi_payment())

    @api.depends('l10n_mx_edi_invoice_document_ids.state', 'l10n_mx_edi_invoice_document_ids.sat_state',
                 'l10n_mx_edi_payment_document_ids.state', 'l10n_mx_edi_payment_document_ids.sat_state')
    def _compute_l10n_mx_edi_document_ids(self):
        for move in self:
            if move.is_invoice():
                move.l10n_mx_edi_document_ids = [Command.set(move.l10n_mx_edi_invoice_document_ids.ids)]
            elif move._l10n_mx_edi_is_cfdi_payment():
                move.l10n_mx_edi_document_ids = [Command.set(move.l10n_mx_edi_payment_document_ids.ids)]
            else:
                move.l10n_mx_edi_document_ids = [Command.clear()]

    @api.depends('l10n_mx_edi_invoice_document_ids.state', 'l10n_mx_edi_invoice_document_ids.sat_state',
                 'l10n_mx_edi_payment_document_ids.state', 'l10n_mx_edi_payment_document_ids.sat_state')
    def _compute_l10n_mx_edi_cfdi_state_and_attachment(self):
        for move in self:
            move.l10n_mx_edi_cfdi_sat_state = None
            move.l10n_mx_edi_cfdi_state = None
            move.l10n_mx_edi_cfdi_attachment_id = None
            move.l10n_mx_edi_invoice_cancellation_reason = None
            if move.is_invoice():
                # Compute the SAT & the PAC states in 2 different loops.
                # In case of a request cancellation that failed, the SAT state needs
                # to be retrieved from the document corresponding to the request cancellation.
                # However, the PAC state needs to be retrieved from the original 'invoice_sent'
                # document.
                documents = move.l10n_mx_edi_invoice_document_ids.sorted()

                # 'l10n_mx_edi_cfdi_sat_state'.
                for doc in documents.filtered(lambda doc: doc.state in {
                    'invoice_sent',
                    'invoice_cancel_requested',
                    'invoice_cancel',
                    'ginvoice_sent',
                    'ginvoice_cancel',
                }):
                    if doc.sat_state != 'skip':
                        move.l10n_mx_edi_cfdi_sat_state = doc.sat_state
                        break

                # 'l10n_mx_edi_cfdi_state' / 'l10n_mx_edi_cfdi_attachment_id'.
                for doc in documents:
                    if doc.state == 'invoice_sent':
                        move.l10n_mx_edi_cfdi_state = 'sent'
                        move.l10n_mx_edi_cfdi_attachment_id = doc.attachment_id
                        break
                    elif doc.state == 'invoice_received':
                        move.l10n_mx_edi_cfdi_state = 'received'
                        move.l10n_mx_edi_cfdi_attachment_id = doc.attachment_id
                        break
                    elif doc.state == 'ginvoice_sent':
                        move.l10n_mx_edi_cfdi_state = 'global_sent'
                        move.l10n_mx_edi_cfdi_attachment_id = doc.attachment_id
                        break
                    elif doc.state == 'invoice_cancel_requested' and doc.sat_state == 'not_defined':
                        move.l10n_mx_edi_cfdi_state = 'cancel_requested'
                        move.l10n_mx_edi_cfdi_attachment_id = doc.attachment_id
                        move.l10n_mx_edi_invoice_cancellation_reason = doc.cancellation_reason
                        break
                    elif doc.state == 'invoice_cancel':
                        move.l10n_mx_edi_cfdi_state = 'cancel'
                        move.l10n_mx_edi_cfdi_attachment_id = doc.attachment_id
                        move.l10n_mx_edi_invoice_cancellation_reason = doc.cancellation_reason
                        break
                    elif doc.state == 'ginvoice_cancel' and doc.cancellation_reason != '01':
                        move.l10n_mx_edi_cfdi_state = 'global_cancel'
                        move.l10n_mx_edi_cfdi_attachment_id = doc.attachment_id
                        move.l10n_mx_edi_invoice_cancellation_reason = doc.cancellation_reason
                        break
            elif move._l10n_mx_edi_is_cfdi_payment():
                for doc in move.l10n_mx_edi_payment_document_ids.sorted():
                    if doc.state == 'payment_sent':
                        move.l10n_mx_edi_cfdi_sat_state = doc.sat_state
                        move.l10n_mx_edi_cfdi_state = 'sent'
                        move.l10n_mx_edi_cfdi_attachment_id = doc.attachment_id
                        break
                    elif doc.state == 'payment_cancel':
                        move.l10n_mx_edi_cfdi_sat_state = doc.sat_state
                        move.l10n_mx_edi_cfdi_state = 'cancel'
                        move.l10n_mx_edi_cfdi_attachment_id = doc.attachment_id
                        move.l10n_mx_edi_invoice_cancellation_reason = doc.cancellation_reason
                        break

    @api.depends('l10n_mx_edi_invoice_document_ids.state')
    def _compute_l10n_mx_edi_update_payments_needed(self):
        payments_diff = self._origin\
            .with_context(bin_size=False)\
            ._l10n_mx_edi_cfdi_invoice_get_payments_diff()
        for move in self:
            move.l10n_mx_edi_update_payments_needed = bool(
                move in payments_diff['to_remove']
                or move in payments_diff['need_update']
                or payments_diff['to_process']
            )

    @api.depends('l10n_mx_edi_payment_document_ids.state')
    def _compute_l10n_mx_edi_force_pue_payment_needed(self):
        for move in self:
            force_pue = False
            if move._l10n_mx_edi_is_cfdi_payment() and not move.l10n_mx_edi_cfdi_state:
                for doc in move.l10n_mx_edi_payment_document_ids.sorted():
                    if doc.state == 'payment_sent_pue':
                        force_pue = True
                        break
            move.l10n_mx_edi_force_pue_payment_needed = force_pue

    @api.depends('state', 'l10n_mx_edi_cfdi_state', 'l10n_mx_edi_cfdi_sat_state')
    def _compute_l10n_mx_edi_update_sat_needed(self):
        for move in self:
            if move.is_invoice():
                documents = move.l10n_mx_edi_invoice_document_ids
            elif move._l10n_mx_edi_is_cfdi_payment():
                documents = move.l10n_mx_edi_payment_document_ids
            else:
                move.l10n_mx_edi_update_sat_needed = False
                continue
            move.l10n_mx_edi_update_sat_needed = bool(documents.filtered_domain(
                documents._get_update_sat_status_domain(from_cron=False)
            ))

    @api.depends('l10n_mx_edi_cfdi_attachment_id')
    def _compute_l10n_mx_edi_cfdi_uuid(self):
        '''Fill the invoice fields from the cfdi values.
        '''
        for move in self:
            if move.l10n_mx_edi_cfdi_attachment_id:
                cfdi_infos = self.env['l10n_mx_edi.document']._decode_cfdi_attachment(move.l10n_mx_edi_cfdi_attachment_id.raw)
                move.l10n_mx_edi_cfdi_uuid = cfdi_infos.get('uuid')
            else:
                move.l10n_mx_edi_cfdi_uuid = None

    @api.depends('l10n_mx_edi_cfdi_attachment_id', 'l10n_mx_edi_cfdi_state')
    def _compute_cfdi_values(self):
        '''Fill the invoice fields from the cfdi values.
        '''
        for move in self:
            cfdi_infos = self.env['l10n_mx_edi.document']._decode_cfdi_attachment(move.l10n_mx_edi_cfdi_attachment_id.raw)
            move.l10n_mx_edi_cfdi_supplier_rfc = cfdi_infos.get('supplier_rfc')
            move.l10n_mx_edi_cfdi_customer_rfc = cfdi_infos.get('customer_rfc')
            move.l10n_mx_edi_cfdi_amount = cfdi_infos.get('amount_total')

    @api.depends('move_type', 'invoice_date_due', 'invoice_date', 'invoice_payment_term_id')
    def _compute_l10n_mx_edi_payment_policy(self):
        for move in self:
            move.l10n_mx_edi_payment_policy = False

            if move.is_invoice(include_receipts=True) \
                and move.l10n_mx_edi_is_cfdi_needed \
                and move.invoice_date_due \
                and move.invoice_date:

                # By default PUE means immediate payment and then, no need to send the payments to
                # the SAT except if you explicitely send them.
                move.l10n_mx_edi_payment_policy = 'PUE'

                # In CFDI 3.3 - rule 2.7.1.43 which establish that
                # invoice payment term should be PPD as soon as the due date
                # is after the last day of  the month (the month of the invoice date).
                # Also, 'to public' invoice should remain PUE.
                if (
                    move.move_type == 'out_invoice'
                    and not move.l10n_mx_edi_cfdi_to_public
                    and (
                        move.invoice_date_due.month > move.invoice_date.month
                        or move.invoice_date_due.year > move.invoice_date.year
                        or len(move.invoice_payment_term_id.line_ids) > 1
                    )
                ):
                    move.l10n_mx_edi_payment_policy = 'PPD'

    @api.depends('l10n_mx_edi_is_cfdi_needed', 'l10n_mx_edi_cfdi_origin', 'partner_id', 'company_id')
    def _compute_l10n_mx_edi_cfdi_to_public(self):
        for move in self:
            if move.move_type == 'out_refund' and 'global_sent' in set(move._l10n_mx_edi_get_refund_original_invoices().mapped('l10n_mx_edi_cfdi_state')):
                move.l10n_mx_edi_cfdi_to_public = True
            elif (
                not move.l10n_mx_edi_cfdi_to_public
                and move.l10n_mx_edi_is_cfdi_needed
                and move.partner_id
                and move.company_id
            ):
                cfdi_values = self.env['l10n_mx_edi.document']._get_company_cfdi_values(move.company_id)
                self.env['l10n_mx_edi.document']._add_customer_cfdi_values(
                    cfdi_values,
                    customer=move.partner_id,
                )
                move.l10n_mx_edi_cfdi_to_public = cfdi_values['receptor']['rfc'] == 'XAXX010101000'
            else:
                move.l10n_mx_edi_cfdi_to_public = move.l10n_mx_edi_cfdi_to_public

    @api.depends('journal_id', 'statement_line_id', 'partner_id')
    def _compute_l10n_mx_edi_payment_method_id(self):
        otros_payment_method = self.env.ref('l10n_mx_edi.payment_method_otros', raise_if_not_found=False)
        transferencia_payment_method = self.env.ref('l10n_mx_edi.payment_method_transferencia', raise_if_not_found=False)
        for move in self:
            if move.country_code != 'MX':
                move.l10n_mx_edi_payment_method_id = False
                continue
            if move.is_invoice(include_receipts=True):
                payment_method = move.partner_id.l10n_mx_edi_payment_method_id or move.l10n_mx_edi_payment_method_id
            else:
                payment_method = move.l10n_mx_edi_payment_method_id or move.partner_id.l10n_mx_edi_payment_method_id
            move.l10n_mx_edi_payment_method_id = (
                payment_method or
                (move._l10n_mx_edi_is_cfdi_payment() and transferencia_payment_method) or
                move.journal_id.l10n_mx_edi_payment_method_id or
                otros_payment_method
            )

    @api.depends('partner_id')
    def _compute_l10n_mx_edi_usage(self):
        for move in self:
            if move.country_code == 'MX':
                move.l10n_mx_edi_usage = (
                    move.partner_id.l10n_mx_edi_usage or
                    move.l10n_mx_edi_usage or
                    'G03'
                )
            else:
                move.l10n_mx_edi_usage = False

    @api.depends('l10n_mx_edi_cfdi_uuid')
    def _compute_l10n_mx_edi_cfdi_cancel_id(self):
        for move in self:
            if move.company_id and move.l10n_mx_edi_cfdi_uuid:
                move.l10n_mx_edi_cfdi_cancel_id = move.search(
                    [
                        ('l10n_mx_edi_cfdi_origin', '=like', f'04|{move.l10n_mx_edi_cfdi_uuid}%'),
                        ('company_id', '=', move.company_id.id)
                    ],
                    limit=1,
                )
            else:
                move.l10n_mx_edi_cfdi_cancel_id = None

    @api.depends('l10n_mx_edi_cfdi_uuid')
    def _compute_duplicated_ref_ids(self):
        return super()._compute_duplicated_ref_ids()

    @api.depends('l10n_mx_edi_cfdi_state', 'l10n_mx_edi_cfdi_sat_state')
    def _compute_show_reset_to_draft_button(self):
        # EXTENDS 'account'
        # When the PAC approved the cancellation but we are awaiting the SAT confirmation,
        # don't allow to reset draft the invoice.
        super()._compute_show_reset_to_draft_button()
        for move in self:
            if (
                move.show_reset_to_draft_button
                and move.l10n_mx_edi_cfdi_state not in ('cancel', 'received', False)
                and move.state == 'posted'
            ):
                move.show_reset_to_draft_button = False

    # -------------------------------------------------------------------------
    # CONSTRAINTS
    # -------------------------------------------------------------------------

    @api.constrains('l10n_mx_edi_cfdi_origin')
    def _check_l10n_mx_edi_cfdi_origin(self):
        error_message = _(
            "The following CFDI origin %s is invalid and must match the "
            "<code>|<uuid1>,<uuid2>,...,<uuidn> template.\n"
            "Here are the specification of this value:\n"
            "- 01: Nota de crédito\n"
            "- 02: Nota de débito de los documentos relacionados\n"
            "- 03: Devolución de mercancía sobre facturas o traslados previos\n"
            "- 04: Sustitución de los CFDI previos\n"
            "- 05: Traslados de mercancias facturados previamente\n"
            "- 06: Factura generada por los traslados previos\n"
            "- 07: CFDI por aplicación de anticipo\n"
            "For example: 01|89966ACC-0F5C-447D-AEF3-3EED22E711EE,89966ACC-0F5C-447D-AEF3-3EED22E711EE"
        )

        for move in self.filtered('l10n_mx_edi_cfdi_origin'):
            cfdi_values = {}
            self.env['l10n_mx_edi.document']._add_document_origin_cfdi_values(cfdi_values, move.l10n_mx_edi_cfdi_origin)
            if not cfdi_values['tipo_relacion'] or not cfdi_values['cfdi_relationado_list']:
                raise ValidationError(error_message % move.l10n_mx_edi_cfdi_origin)

    # -------------------------------------------------------------------------
    # BUSINESS METHODS
    # -------------------------------------------------------------------------

    @api.model
    def fields_get(self, allfields=None, attributes=None):
        # TODO: remove in master
        res = super().fields_get(allfields, attributes)

        existing_selection = res.get('l10n_mx_edi_cfdi_state', {}).get('selection')
        if existing_selection is None:
            return res

        cancel_requested_state = next(x for x in self._fields['l10n_mx_edi_cfdi_state'].selection if x[0] == 'cancel_requested')
        need_update = cancel_requested_state not in existing_selection
        if need_update:
            self.env['ir.model.fields'].invalidate_model(['selection_ids'])
            self.env['ir.model.fields.selection']._update_selection(
                'account.move',
                'l10n_mx_edi_cfdi_state',
                self._fields['l10n_mx_edi_cfdi_state'].selection,
            )
            self.env['ir.model.fields.selection']._update_selection(
                'l10n_mx_edi.document',
                'state',
                self.env['l10n_mx_edi.document']._fields['state'].selection,
            )
            self.env.registry.clear_cache()

        return res

    def _post(self, soft=True):
        # OVERRIDE
        mexico_tz = self.env['l10n_mx_edi.certificate'].sudo()._get_timezone()
        certificate_date = datetime.now(mexico_tz)

        for move in self.filtered('l10n_mx_edi_is_cfdi_needed'):

            cfdi_values = self.env['l10n_mx_edi.document']._get_company_cfdi_values(move.company_id)
            self.env['l10n_mx_edi.document']._add_customer_cfdi_values(
                cfdi_values,
                customer=move.partner_id,
            )
            move.l10n_mx_edi_post_time = fields.Datetime.to_string(move._l10n_mx_edi_get_datetime_now_with_mx_timezone(cfdi_values))

            # Assign time and date coming from a certificate.
            if move.is_invoice() and move.l10n_mx_edi_is_cfdi_needed and not move.invoice_date:
                move.invoice_date = certificate_date.date()

        return super()._post(soft=soft)

    def _l10n_mx_edi_need_cancel_request(self):
        self.ensure_one()
        return (
            self.l10n_mx_edi_cfdi_state == 'sent'
            and self.l10n_mx_edi_cfdi_attachment_id
            and (
                not self.l10n_mx_edi_cfdi_cancel_id
                or self.l10n_mx_edi_cfdi_cancel_id.l10n_mx_edi_cfdi_state
            )
        )

    def _need_cancel_request(self):
        # EXTENDS 'account'
        return super()._need_cancel_request() or self._l10n_mx_edi_need_cancel_request()

    def button_request_cancel(self):
        # EXTENDS 'account'
        super().button_request_cancel()

        # Check the CFDI state to restrict this code to MX only.
        if self._l10n_mx_edi_need_cancel_request():
            doc = self.l10n_mx_edi_document_ids.filtered(lambda x: (
                x.attachment_uuid == self.l10n_mx_edi_cfdi_uuid
                and x.state in ('invoice_sent', 'payment_sent')
            ))[0]
            return doc.action_request_cancel()

    def _reverse_moves(self, default_values_list=None, cancel=False):
        # OVERRIDE
        # The '01' code is used to indicate the document is a credit note.
        if not default_values_list:
            default_values_list = [{}] * len(self)

        for default_vals, move in zip(default_values_list, self):
            if move.l10n_mx_edi_cfdi_uuid:
                default_vals['l10n_mx_edi_cfdi_origin'] = move._l10n_mx_edi_write_cfdi_origin('01', [move.l10n_mx_edi_cfdi_uuid])
        return super()._reverse_moves(default_values_list, cancel=cancel)

    def _get_mail_thread_data_attachments(self):
        # EXTENDS 'account'
        return super()._get_mail_thread_data_attachments() \
            - self.l10n_mx_edi_payment_document_ids.attachment_id \
            + self.l10n_mx_edi_cfdi_attachment_id

    @api.model
    def get_invoice_localisation_fields_required_to_invoice(self, country_id):
        res = super().get_invoice_localisation_fields_required_to_invoice(country_id)
        if country_id.code == 'MX':
            res.extend([self.env['ir.model.fields']._get(self._name, 'l10n_mx_edi_usage')])
        return res

    def _get_name_invoice_report(self):
        # EXTENDS account
        self.ensure_one()
        if self.l10n_mx_edi_cfdi_state == 'sent' and self.l10n_mx_edi_cfdi_attachment_id:
            return 'l10n_mx_edi.report_invoice_document'
        return super()._get_name_invoice_report()

    def _get_edi_doc_attachments_to_export(self):
        # EXTENDS 'account'
        return super()._get_edi_doc_attachments_to_export() + self.l10n_mx_edi_cfdi_attachment_id

    def _fetch_duplicate_supplier_reference(self, only_posted=False):
        # EXTENDS account
        # We check whether there are moves with the same fiscal folio if we have Mexican bills
        mx_vendor_bills = self.filtered(lambda m: m.is_purchase_document() and m.l10n_mx_edi_cfdi_uuid and m._origin.id)
        if not mx_vendor_bills:
            return super()._fetch_duplicate_supplier_reference(only_posted=only_posted)

        self.env['account.move'].flush_model(('company_id', 'move_type', 'l10n_mx_edi_cfdi_uuid'))

        self.env.cr.execute(
            """
              SELECT move.id AS move_id,
                     ARRAY_AGG(duplicate_move.id) AS duplicate_ids
                FROM account_move AS move
                JOIN account_move AS duplicate_move
                  ON move.company_id = duplicate_move.company_id
                 AND move.move_type = duplicate_move.move_type
                 AND move.id != duplicate_move.id
                 AND move.l10n_mx_edi_cfdi_uuid = duplicate_move.l10n_mx_edi_cfdi_uuid
               WHERE move.id IN %(moves)s
            GROUP BY move.id
            """,
            {
                'moves': tuple(mx_vendor_bills.ids),
            },
        )
        folio_fiscal_duplicates = {
            self.env['account.move'].browse(res['move_id']): self.env['account.move'].browse(res['duplicate_ids'])
            for res in self.env.cr.dictfetchall()
        }
        move_duplicates = super()._fetch_duplicate_supplier_reference(only_posted=only_posted)
        for move, duplicates in folio_fiscal_duplicates.items():
            move_duplicates[move] = move_duplicates.get(move, self.env['account.move']) | duplicates
        return move_duplicates

    # -------------------------------------------------------------------------
    # CFDI Generation: Generic
    # -------------------------------------------------------------------------

    def _l10n_mx_edi_get_datetime_now_with_mx_timezone(self, cfdi_values):
        """ Get datetime.now() but with the mexican timezone depending the CFDI issued address.

        :param cfdi_values: The values to create the CFDI collected so far.
        :return: A datetime object.
        """
        self.ensure_one()
        issued_address = cfdi_values['receptor']['issued_address']
        tz = issued_address._l10n_mx_edi_get_cfdi_timezone()
        tz_force = self.env['ir.config_parameter'].sudo().get_param(f'l10n_mx_edi_tz_{self.journal_id.id}', default=None)
        if tz_force:
            tz = timezone(tz_force)

        return datetime.now(tz)

    def _l10n_mx_edi_add_common_cfdi_values(self, cfdi_values):
        ''' Populate cfdi values to generate a cfdi for a journal entry. '''
        self.ensure_one()
        Document = self.env['l10n_mx_edi.document']
        Document._add_base_cfdi_values(cfdi_values)
        Document._add_currency_cfdi_values(cfdi_values, self.currency_id)
        Document._add_document_name_cfdi_values(cfdi_values, self.name)
        Document._add_document_origin_cfdi_values(cfdi_values, self.l10n_mx_edi_cfdi_origin)

    # -------------------------------------------------------------------------
    # CFDI Generation: Invoices
    # -------------------------------------------------------------------------

    def _l10n_mx_edi_cfdi_invoice_line_ids(self):
        """ Get the invoice lines to be considered when creating the CFDI.

        :return: A recordset of invoice lines.
        """
        self.ensure_one()
        return self.invoice_line_ids.filtered(lambda line: (
            line.display_type == 'product'
            and not line.currency_id.is_zero(line.price_unit * line.quantity)
        ))

    def _l10n_mx_edi_cfdi_check_invoice_config(self):
        """ Prepare the CFDI xml for the invoice. """
        self.ensure_one()
        errors = []

        # == Check the 'l10n_mx_edi_decimal_places' field set on the currency  ==
        currency_precision = self.currency_id.l10n_mx_edi_decimal_places
        if currency_precision is False:
            errors.append(_(
                "The SAT does not provide information for the currency %s.\n"
                "You must get manually a key from the PAC to confirm the "
                "currency rate is accurate enough.",
                self.currency_id,
            ))

        # == Check the invoice ==
        invoice_lines = self._l10n_mx_edi_cfdi_invoice_line_ids()
        if not invoice_lines:
            errors.append(_("The invoice must contain at least one positive line to generate the CFDI."))
        negative_lines = invoice_lines.filtered(lambda line: line.price_subtotal < 0)
        if negative_lines:
            # Line having a negative amount is not allowed.
            if not self.env['l10n_mx_edi.document']._is_cfdi_negative_lines_allowed():
                errors.append(_(
                    "Invoice lines having a negative amount are not allowed to generate the CFDI. "
                    "Please create a credit note instead.",
                ))
        invalid_unspcs_products = invoice_lines.product_id.filtered(lambda product: not product.unspsc_code_id)
        if invalid_unspcs_products:
            errors.append(_(
                "You need to define an 'UNSPSC Product Category' on the following products: %s",
                ', '.join(invalid_unspcs_products.mapped('display_name')),
            ))
        return errors

    def _l10n_mx_edi_add_invoice_cfdi_values(self, cfdi_values, percentage_paid=None, global_invoice=False):
        self.ensure_one()
        Document = self.env['l10n_mx_edi.document']

        base_lines = [
            {
                **invl._convert_to_tax_base_line_dict(),
                'uom': invl.product_uom_id,
                'name': invl.name,
            }
            for invl in self._l10n_mx_edi_cfdi_invoice_line_ids()
        ]
        Document._add_base_lines_tax_amounts(base_lines, cfdi_values=cfdi_values)
        if global_invoice and self.reversal_move_id:
            refund_base_lines = [
                {
                    **invl._convert_to_tax_base_line_dict(),
                    'uom': invl.product_uom_id,
                    'name': invl.name,
                }
                for invl in self.reversal_move_id._l10n_mx_edi_cfdi_invoice_line_ids()
            ]
            for refund_base_line in refund_base_lines:
                refund_base_line['quantity'] *= -1
                refund_base_line['price_subtotal'] *= -1
            Document._add_base_lines_tax_amounts(refund_base_lines, cfdi_values=cfdi_values)
            base_lines += refund_base_lines

        # Manage the negative lines.
        lines_dispatching = Document._dispatch_cfdi_base_lines(base_lines)
        if lines_dispatching['orphan_negative_lines']:
            cfdi_values['errors'] = [_("Failed to distribute some negative lines")]
            return
        cfdi_lines = lines_dispatching['result_lines']
        if not cfdi_lines:
            cfdi_values['errors'] = ['empty_cfdi']
            return

        self._l10n_mx_edi_add_common_cfdi_values(cfdi_values)
        cfdi_values['tipo_de_comprobante'] = 'I' if self.move_type == 'out_invoice' else 'E'
        Document._add_customer_cfdi_values(
            cfdi_values,
            customer=self.partner_id,
            usage=self.l10n_mx_edi_usage,
            to_public=self.l10n_mx_edi_cfdi_to_public,
        )
        Document._add_tax_objected_cfdi_values(cfdi_values, cfdi_lines)
        Document._add_base_lines_cfdi_values(
            cfdi_values,
            cfdi_lines,
            percentage_paid=percentage_paid,
        )

        # Date.
        timezoned_now = self._l10n_mx_edi_get_datetime_now_with_mx_timezone(cfdi_values)
        timezoned_today = timezoned_now.date()
        if self.invoice_date >= timezoned_today:
            cfdi_values['fecha'] = timezoned_now.strftime(CFDI_DATE_FORMAT)
        else:
            cfdi_time = datetime.strptime('23:59:00', '%H:%M:%S').time()
            cfdi_values['fecha'] = datetime\
                .combine(fields.Datetime.from_string(self.invoice_date), cfdi_time)\
                .strftime(CFDI_DATE_FORMAT)

        # Payment terms.
        cfdi_values['metodo_pago'] = self.l10n_mx_edi_payment_policy
        if cfdi_values['metodo_pago'] == 'PPD':
            cfdi_values['forma_pago'] = '99'
        else:
            cfdi_values['forma_pago'] = (self.l10n_mx_edi_payment_method_id.code or '').replace('NA', '99')
        cfdi_values['condiciones_de_pago'] = self.invoice_payment_term_id.name

        # Currency.
        if self.currency_id.name == 'MXN':
            cfdi_values['tipo_cambio'] = None
        else:
            mxn_currency = self.company_currency_id
            current_currency = self.currency_id
            cfdi_values["tipo_cambio"] = current_currency._get_conversion_rate(
                from_currency=current_currency,
                to_currency=mxn_currency,
                company=self.company_id,
                date=self.date,
            ) if self.amount_total else 1.0

    def _l10n_mx_edi_get_invoice_cfdi_filename(self):
        """ Get the filename of the CFDI.

        :return: The filename as a string.
        """
        self.ensure_one()
        return f"{self.journal_id.code}-{self.name}-MX-Invoice-4.0.xml".replace('/', '')

    # -------------------------------------------------------------------------
    # CFDI Generation: Payments
    # -------------------------------------------------------------------------

    def _l10n_mx_edi_add_payment_cfdi_values(self, cfdi_values, pay_results):
        """ Prepare the values to render the payment cfdi.

        :param cfdi_values: Prepared cfdi_values.
        :param pay_results: The amounts to consider for each invoice.
                            See '_l10n_mx_edi_cfdi_payment_get_reconciled_invoice_values'.
        :return: The dictionary to render the xml.
        """
        self.ensure_one()

        self._l10n_mx_edi_add_common_cfdi_values(cfdi_values)
        company = cfdi_values['company']
        company_curr = company.currency_id

        # Misc.
        cfdi_values['exportacion'] = '01'
        cfdi_values['forma_de_pago'] = (self.l10n_mx_edi_payment_method_id.code or '').replace('NA', '99')
        cfdi_values['moneda'] = self.currency_id.name
        cfdi_values['num_operacion'] = self.ref

        # Amounts.
        total_in_payment_curr = sum(x['payment_amount_currency'] for x in pay_results['invoice_results'])
        total_in_company_curr = sum(x['balance'] + x['payment_exchange_balance'] for x in pay_results['invoice_results'])
        if self.currency_id == company_curr:
            cfdi_values['monto'] = total_in_company_curr
        else:
            cfdi_values['monto'] = total_in_payment_curr

        # Exchange rate.
        # 'tipo_cambio' is a conditional attribute used to express the exchange rate of the currency on the date the
        # payment was made.
        # The value must reflect the number of Mexican pesos that are equivalent to a unit of the currency indicated
        # in the 'moneda' attribute.
        # It is required when the MonedaP attribute is different from MXN.
        cfdi_values['tipo_cambio_dp'] = 6
        if self.currency_id == company_curr:
            payment_rate = None
        else:
            raw_payment_rate = abs(total_in_company_curr / total_in_payment_curr) if total_in_payment_curr else 0.0
            payment_rate = float_round(raw_payment_rate, precision_digits=cfdi_values['tipo_cambio_dp'])
        cfdi_values['tipo_cambio'] = payment_rate

        # === Create the list of invoice data ===
        invoice_values_list = []
        for invoice_values in pay_results['invoice_results']:
            invoice = invoice_values['invoice']

            inv_cfdi_values = self.env['l10n_mx_edi.document']._get_company_cfdi_values(invoice.company_id)
            self.env['l10n_mx_edi.document']._add_certificate_cfdi_values(inv_cfdi_values)
            invoice._l10n_mx_edi_add_invoice_cfdi_values(inv_cfdi_values)

            # Apply the percentage paid to the tax amounts.
            if invoice.amount_total:
                percentage_paid = abs(invoice_values['reconciled_amount'] / invoice.amount_total)
            else:
                percentage_paid = 0.0
            for key in ('retenciones_list', 'traslados_list'):
                for tax_values in inv_cfdi_values[key]:
                    for tax_key in ('base', 'importe'):
                        if tax_values[tax_key] is not None:
                            tax_values[tax_key] = invoice.currency_id.round(tax_values[tax_key] * percentage_paid)

                    # CRP20261:
                    # - 'base' * 'tasa_o_cuota' must give 'importe' with 0.01 rounding error allowed.
                    # Suppose an invoice of 5 * 0.47 with 16% tax. Each line gives a tax amount of 0.08 so 0.40 for the whole invoice.
                    # However, 5 * 0.47 = 2.35 and 2.35 * 0.16 = 0.38 so the constraint is failing.
                    # - 'base' + 'importe' must be exactly equal to the part that is actually paid.
                    # Using the same example, we need to report 2.35 + 0.40 = 2.75
                    # => To solve that, let's proceed backward. 2.75 * 0.16 / 1.16 = 0.38 (importe) and 2.75 - 0.38 = 2.27 (base).
                    if (
                        company.tax_calculation_rounding_method == 'round_per_line'
                        and all(tax_values[key] is not None for key in ('base', 'importe', 'tasa_o_cuota'))
                    ):
                        total = tax_values['base'] + tax_values['importe']
                        percent = tax_values['tasa_o_cuota']
                        tax_values['importe'] = invoice.currency_id.round(total * percent / (1 + percent))
                        tax_values['base'] = invoice.currency_id.round(total - tax_values['importe'])

            # 'equivalencia' (rate) is a conditional attribute used to express the exchange rate according to the currency
            # registered in the document related. It is required when the currency of the related document is different
            # from the payment currency.
            # The number of units of the currency must be recorded indicated in the related document that are
            # equivalent to a unit of the currency of the payment.
            if invoice.currency_id == self.currency_id:
                # Same currency.
                rate = None
            elif invoice.currency_id == company_curr != self.currency_id:
                # Adapt the payment rate to find the reconciled amount of the invoice but expressed in payment currency.
                balance = invoice_values['balance'] + invoice_values['invoice_exchange_balance']
                amount_currency = invoice_values['payment_amount_currency']
                rate = abs(balance / amount_currency) if amount_currency else 0.0
            elif self.currency_id == company_curr != invoice.currency_id:
                # Adapt the invoice rate to find the reconciled amount of the payment but expressed in invoice currency.
                balance = invoice_values['balance'] + invoice_values['payment_exchange_balance']
                rate = abs(invoice_values['invoice_amount_currency'] / balance) if balance else 0.0
            elif invoice_values['payment_amount_currency']:
                # Both are expressed in different currencies.
                rate = abs(invoice_values['invoice_amount_currency'] / invoice_values['payment_amount_currency'])
            else:
                rate = 0.0

            invoice_values_list.append({
                **inv_cfdi_values,
                'id_documento': invoice.l10n_mx_edi_cfdi_uuid,
                'equivalencia': rate,
                'num_parcialidad': invoice_values['number_of_payments'],
                'imp_pagado': invoice_values['reconciled_amount'],
                'imp_saldo_ant': invoice_values['amount_residual_before'],
                'imp_saldo_insoluto': invoice_values['amount_residual_after'],
            })
        cfdi_values['docto_relationado_list'] = invoice_values_list

        # Customer.
        rfcs = set(x['receptor']['rfc'] for x in invoice_values_list)
        if len(rfcs) > 1:
            cfdi_values['errors'] = [_("You can't register a payment for invoices having different RFCs.")]
            return

        customer_values = invoice_values_list[0]['receptor']
        customer = customer_values['customer']
        cfdi_values['receptor'] = customer_values
        cfdi_values['lugar_expedicion'] = cfdi_values['issued_address'].zip

        # Date.
        cfdi_date = datetime.combine(fields.Datetime.from_string(self.date), datetime.strptime('12:00:00', '%H:%M:%S').time())
        cfdi_values['fecha'] = self._l10n_mx_edi_get_datetime_now_with_mx_timezone(cfdi_values).strftime(CFDI_DATE_FORMAT)
        cfdi_values['fecha_pago'] = cfdi_date.strftime(CFDI_DATE_FORMAT)

        # Bank information.
        payment_method_code = self.l10n_mx_edi_payment_method_id.code
        is_payment_code_emitter_ok = payment_method_code in ('02', '03', '04', '05', '06', '28', '29', '99')
        is_payment_code_receiver_ok = payment_method_code in ('02', '03', '04', '05', '28', '29', '99')
        is_payment_code_bank_ok = payment_method_code in ('02', '03', '04', '28', '29', '99')

        bank_account = customer.bank_ids.filtered(lambda x: x.company_id.id in (False, company.id))[:1]

        partner_bank = bank_account.bank_id
        if partner_bank.country and partner_bank.country.code != 'MX':
            partner_bank_vat = 'XEXX010101000'
        else:  # if no partner_bank (e.g. cash payment), partner_bank_vat is not set.
            partner_bank_vat = partner_bank.l10n_mx_edi_vat

        payment_account_ord = re.sub(r'\s+', '', bank_account.acc_number or '') or None
        payment_account_receiver = re.sub(r'\s+', '', self.journal_id.bank_account_id.acc_number or '') or None

        cfdi_values.update({
            'rfc_emisor_cta_ord': is_payment_code_emitter_ok and partner_bank_vat,
            'nom_banco_ord_ext': is_payment_code_bank_ok and partner_bank.name,
            'cta_ordenante': is_payment_code_emitter_ok and payment_account_ord,
            'rfc_emisor_cta_ben': is_payment_code_receiver_ok and self.journal_id.bank_account_id.bank_id.l10n_mx_edi_vat,
            'cta_beneficiario': is_payment_code_receiver_ok and payment_account_receiver,
        })

        # Taxes.
        cfdi_values.update({
            'monto_total_pagos': total_in_company_curr,
            'mxn_digits': company_curr.decimal_places,
        })

        def update_tax_amount(key, amount):
            if key not in cfdi_values:
                cfdi_values[key] = 0.0
            cfdi_values[key] += amount

        def check_transferred_tax_values(tax_values, tag, tax_class, amount):
            return (
                tax_values['impuesto'] == tag
                and tax_values['tipo_factor'] == tax_class
                and company_curr.compare_amounts(tax_values['tasa_o_cuota'] or 0.0, amount) == 0
            )

        withholding_values_map = defaultdict(lambda: {'importe': 0.0})
        transferred_values_map = defaultdict(lambda: {'base': 0.0, 'importe': 0.0})
        pay_rate = cfdi_values['tipo_cambio'] or 1.0
        for cfdi_inv_values in invoice_values_list:
            inv_rate = cfdi_inv_values['equivalencia'] or 1.0
            to_mxn_rate = pay_rate / inv_rate
            for tax_values in cfdi_inv_values['retenciones_list']:
                key = frozendict({'impuesto': tax_values['impuesto']})
                withholding_values_map[key]['importe'] += tax_values['importe'] / inv_rate

                tax_amount_mxn = tax_values['importe'] * to_mxn_rate
                if tax_values['impuesto'] == '001':
                    update_tax_amount('total_retenciones_isr', tax_amount_mxn)
                elif tax_values['impuesto'] == '002':
                    update_tax_amount('total_retenciones_iva', tax_amount_mxn)
                elif tax_values['impuesto'] == '003':
                    update_tax_amount('total_retenciones_ieps', tax_amount_mxn)

            for tax_values in cfdi_inv_values['traslados_list']:
                key = frozendict({
                    'impuesto': tax_values['impuesto'],
                    'tipo_factor': tax_values['tipo_factor'],
                    'tasa_o_cuota': tax_values['tasa_o_cuota']
                })
                tax_amount = tax_values['importe'] or 0.0
                transferred_values_map[key]['base'] += tax_values['base'] / inv_rate
                transferred_values_map[key]['importe'] += tax_amount / inv_rate

                base_amount_mxn = tax_values['base'] * to_mxn_rate
                tax_amount_mxn = tax_amount * to_mxn_rate
                if check_transferred_tax_values(tax_values, '002', 'Tasa', 0.0):
                    update_tax_amount('total_traslados_base_iva0', base_amount_mxn)
                    update_tax_amount('total_traslados_impuesto_iva0', tax_amount_mxn)
                elif check_transferred_tax_values(tax_values, '002', 'Exento', 0.0):
                    update_tax_amount('total_traslados_base_iva_exento', base_amount_mxn)
                elif check_transferred_tax_values(tax_values, '002', 'Tasa', 0.08):
                    update_tax_amount('total_traslados_base_iva8', base_amount_mxn)
                    update_tax_amount('total_traslados_impuesto_iva8', tax_amount_mxn)
                elif check_transferred_tax_values(tax_values, '002', 'Tasa', 0.16):
                    update_tax_amount('total_traslados_base_iva16', base_amount_mxn)
                    update_tax_amount('total_traslados_impuesto_iva16', tax_amount_mxn)

        # Rounding global tax amounts.
        for dictionary in (withholding_values_map, transferred_values_map):
            for values in dictionary.values():
                if 'base' in values:
                    values['base'] = self.currency_id.round(values['base'])
                values['importe'] = self.currency_id.round(values['importe'])

        for key in (
            'total_traslados_base_iva0',
            'total_traslados_impuesto_iva0',
            'total_traslados_base_iva_exento',
            'total_traslados_base_iva8',
            'total_traslados_impuesto_iva8',
            'total_traslados_base_iva16',
            'total_traslados_impuesto_iva16',
            'total_retenciones_isr',
            'total_retenciones_iva',
            'total_retenciones_ieps',
        ):
            if key in cfdi_values:
                cfdi_values[key] = company_curr.round(cfdi_values[key])
            else:
                cfdi_values[key] = None

        cfdi_values['retenciones_list'] = [
            {**k, **v}
            for k, v in withholding_values_map.items()
        ]
        cfdi_values['traslados_list'] = [
            {**k, **v}
            for k, v in transferred_values_map.items()
        ]

        # Cleanup attributes for Exento taxes.
        for tax_values in cfdi_values['traslados_list']:
            if tax_values['tipo_factor'] == 'Exento':
                tax_values['importe'] = None

    # -------------------------------------------------------------------------
    # CFDI: DOCUMENTS
    # -------------------------------------------------------------------------

    def _l10n_mx_edi_cfdi_invoice_document_sent_failed(self, error, cfdi_filename=None, cfdi_str=None):
        """ Create/update the invoice document for 'sent_failed'.
        The parameters are provided by '_l10n_mx_edi_prepare_invoice_cfdi'.

        :param error:           The error.
        :param cfdi_filename:   The optional filename of the cfdi.
        :param cfdi_str:        The optional content of the cfdi.
        :return:                The created/updated document.
        """
        self.ensure_one()

        document_values = {
            'move_id': self.id,
            'invoice_ids': [Command.set(self.ids)],
            'state': 'invoice_sent_failed',
            'sat_state': None,
            'message': error,
        }
        if cfdi_filename and cfdi_str:
            document_values['attachment_id'] = {
                'name': cfdi_filename,
                'raw': cfdi_str,
            }
        return self.env['l10n_mx_edi.document']._create_update_invoice_document_from_invoice(self, document_values)

    def _l10n_mx_edi_cfdi_invoice_document_sent(self, cfdi_filename, cfdi_str):
        """ Create/update the invoice document for 'sent'.
        The parameters are provided by '_l10n_mx_edi_prepare_invoice_cfdi'.

        :param cfdi_filename:   The filename of the cfdi.
        :param cfdi_str:        The content of the cfdi.
        :return:                The created/updated document.
        """
        self.ensure_one()

        document_values = {
            'move_id': self.id,
            'invoice_ids': [Command.set(self.ids)],
            'state': 'invoice_sent',
            'sat_state': 'not_defined',
            'message': None,
            'attachment_id': {
                'name': cfdi_filename,
                'raw': cfdi_str,
                'description': "CFDI",
            },
        }
        return self.env['l10n_mx_edi.document']._create_update_invoice_document_from_invoice(self, document_values)

    def _l10n_mx_edi_cfdi_invoice_document_empty(self):
        """ Create/update the invoice document for an empty invoice.

        :return: The created/updated document.
        """
        self.ensure_one()

        document_values = {
            'move_id': self.id,
            'invoice_ids': [Command.set(self.ids)],
            'state': 'invoice_sent',
            'sat_state': 'skip',
            'message': None,
        }
        return self.env['l10n_mx_edi.document']._create_update_invoice_document_from_invoice(self, document_values)

    def _l10n_mx_edi_cfdi_invoice_document_cancel_requested_failed(self, error, cfdi, cancel_reason):
        """ Create/update the invoice document for 'cancel_requested_failed'.

        :param error:           The error.
        :param cfdi:            The source cfdi attachment to cancel.
        :param cancel_reason:   The reason for this cancel.
        :return:                The created/updated document.
        """
        self.ensure_one()

        document_values = {
            'move_id': self.id,
            'invoice_ids': [Command.set(self.ids)],
            'state': 'invoice_cancel_requested_failed',
            'sat_state': None,
            'message': error,
            'attachment_id': cfdi.attachment_id.id,
            'cancellation_reason': cancel_reason,
        }
        return self.env['l10n_mx_edi.document']._create_update_invoice_document_from_invoice(self, document_values)

    def _l10n_mx_edi_cfdi_invoice_document_cancel_requested(self, cfdi, cancel_reason):
        """ Create/update the invoice document for 'cancel_requested'.

        :param cfdi:            The source cfdi attachment to cancel.
        :param cancel_reason:   The reason for this cancel.
        :return:                The created/updated document.
        """
        self.ensure_one()

        document_values = {
            'move_id': self.id,
            'invoice_ids': [Command.set(self.ids)],
            'state': 'invoice_cancel_requested',
            'sat_state': 'not_defined',
            'message': None,
            'attachment_id': cfdi.attachment_id.id,
            'cancellation_reason': cancel_reason,
        }
        return self.env['l10n_mx_edi.document']._create_update_invoice_document_from_invoice(self, document_values)

    def _l10n_mx_edi_cfdi_invoice_document_cancel_failed(self, error, cfdi, cancel_reason):
        """ Create/update the invoice document for 'cancel_failed'.

        :param error:           The error.
        :param cfdi:            The source cfdi attachment to cancel.
        :param cancel_reason:   The reason for this cancel.
        :return:                The created/updated document.
        """
        self.ensure_one()

        document_values = {
            'move_id': self.id,
            'invoice_ids': [Command.set(self.ids)],
            'state': 'invoice_cancel_failed',
            'sat_state': None,
            'message': error,
            'attachment_id': cfdi.attachment_id.id,
            'cancellation_reason': cancel_reason,
        }
        return self.env['l10n_mx_edi.document']._create_update_invoice_document_from_invoice(self, document_values)

    def _l10n_mx_edi_cfdi_invoice_document_cancel(self, cfdi, cancel_reason):
        """ Create/update the invoice document for 'cancel'.

        :param cfdi:            The source cfdi attachment to cancel.
        :param cancel_reason:   The reason for this cancel.
        :return:                The created/updated document.
        """
        self.ensure_one()

        document_values = {
            'move_id': self.id,
            'invoice_ids': [Command.set(self.ids)],
            'state': 'invoice_cancel',
            'sat_state': 'not_defined',
            'message': None,
            'attachment_id': cfdi.attachment_id.id,
            'cancellation_reason': cancel_reason,
        }
        return self.env['l10n_mx_edi.document']._create_update_invoice_document_from_invoice(self, document_values)

    def _l10n_mx_edi_cfdi_payment_document_sent_pue(self, invoices):
        """ Create/update the invoice document for 'sent_pue'.
        The parameters are provided by '_l10n_mx_edi_prepare_invoice_cfdi'.

        :param invoices:    The invoices reconciled with the payment and sent to the government.
        :return:            The created/updated document.
        """
        self.ensure_one()

        document_values = {
            'move_id': self.id,
            'invoice_ids': [Command.set(invoices.ids)],
            'state': 'payment_sent_pue',
            'sat_state': None,
            'message': None,
        }
        return self.env['l10n_mx_edi.document']._create_update_payment_document(self, document_values)

    def _l10n_mx_edi_cfdi_payment_document_sent_failed(self, error, invoices, cfdi_filename=None, cfdi_str=None):
        """ Create/update the invoice document for 'sent_failed'.
        The parameters are provided by '_l10n_mx_edi_prepare_invoice_cfdi'.

        :param error:           The error.
        :param cfdi:            The cancelled cfdi attachment.
        :param invoices:        The invoices reconciled with the payment and sent to the government.
        :param cfdi_filename:   The optional filename of the cfdi.
        :param cfdi_str:        The optional content of the cfdi.
        :return:                The created/updated document.
        """
        self.ensure_one()

        document_values = {
            'move_id': self.id,
            'invoice_ids': [Command.set(invoices.ids)],
            'state': 'payment_sent_failed',
            'sat_state': None,
            'message': error,
        }
        if cfdi_filename and cfdi_str:
            document_values['attachment_id'] = {
                'name': cfdi_filename,
                'raw': cfdi_str,
            }
        return self.env['l10n_mx_edi.document']._create_update_payment_document(self, document_values)

    def _l10n_mx_edi_cfdi_payment_document_sent(self, invoices, cfdi_filename, cfdi_str):
        """ Create/update the invoice document for 'sent'.
        The parameters are provided by '_l10n_mx_edi_prepare_invoice_cfdi'.

        :param invoices:        The invoices reconciled with the payment and sent to the government.
        :param cfdi_filename:   The filename of the cfdi.
        :param cfdi_str:        The content of the cfdi.
        :return:                The created/updated document.
        """
        self.ensure_one()

        document_values = {
            'move_id': self.id,
            'invoice_ids': [Command.set(invoices.ids)],
            'state': 'payment_sent',
            'sat_state': 'not_defined',
            'message': None,
            'attachment_id': {
                'name': cfdi_filename,
                'raw': cfdi_str,
                'description': "CFDI",
            },
        }
        return self.env['l10n_mx_edi.document']._create_update_payment_document(self, document_values)

    def _l10n_mx_edi_cfdi_payment_document_cancel_failed(self, error, cfdi, cancel_reason):
        """ Create/update the payment document for 'cancel_failed'.

        :param error:           The error.
        :param cfdi:            The source cfdi attachment to cancel.
        :param cancel_reason:   The reason for this cancel.
        :return:                The created/updated document.
        """
        self.ensure_one()

        document_values = {
            'move_id': self.id,
            'invoice_ids': [Command.set(cfdi.invoice_ids.ids)],
            'state': 'payment_cancel_failed',
            'sat_state': None,
            'message': error,
            'attachment_id': cfdi.attachment_id.id,
            'cancellation_reason': cancel_reason,
        }
        return self.env['l10n_mx_edi.document']._create_update_payment_document(self, document_values)

    def _l10n_mx_edi_cfdi_payment_document_cancel(self, cfdi, cancel_reason):
        """ Create/update the payment document for 'cancel'.

        :param cfdi:            The source cfdi attachment to cancel.
        :param cancel_reason:   The reason for this cancel.
        :return:                The created/updated document.
        """
        self.ensure_one()

        document_values = {
            'move_id': self.id,
            'invoice_ids': [Command.set(cfdi.invoice_ids.ids)],
            'state': 'payment_cancel',
            'sat_state': 'not_defined',
            'message': None,
            'attachment_id': cfdi.attachment_id.id,
            'cancellation_reason': cancel_reason,
        }
        return self.env['l10n_mx_edi.document']._create_update_payment_document(self, document_values)

    def _l10n_mx_edi_cfdi_global_invoice_document_sent_failed(self, error, cfdi_filename=None, cfdi_str=None):
        """ Create/update the global invoice document for 'sent_failed'.

        :param error:           The error.
        :param cfdi_filename:   The optional filename of the cfdi.
        :param cfdi_str:        The optional content of the cfdi.
        :return:                The created/updated document.
        """
        document_values = {
            'invoice_ids': [Command.set(self.ids)],
            'state': 'ginvoice_sent_failed',
            'sat_state': None,
            'message': error,
        }
        if cfdi_filename and cfdi_str:
            document_values['attachment_id'] = {
                'name': cfdi_filename,
                'raw': cfdi_str,
            }
        return self.env['l10n_mx_edi.document']._create_update_global_invoice_document_from_invoices(self, document_values)

    def _l10n_mx_edi_cfdi_global_invoice_document_sent(self, cfdi_filename, cfdi_str):
        """ Create/update the global invoice document for 'sent'.

        :param cfdi_filename:   The filename of the cfdi.
        :param cfdi_str:        The content of the cfdi.
        :return:                The created/updated document.
        """
        document_values = {
            'invoice_ids': [Command.set(self.ids)],
            'state': 'ginvoice_sent',
            'sat_state': 'not_defined',
            'message': None,
            'attachment_id': {
                'name': cfdi_filename,
                'raw': cfdi_str,
                'description': "CFDI",
            },
        }
        return self.env['l10n_mx_edi.document']._create_update_global_invoice_document_from_invoices(self, document_values)

    def _l10n_mx_edi_cfdi_global_invoice_document_empty(self):
        """ Create/update the global invoice document for an empty cfdi.

        :return:                The created/updated document.
        """
        document_values = {
            'invoice_ids': [Command.set(self.ids)],
            'state': 'ginvoice_sent',
            'sat_state': 'skip',
            'message': None,
        }
        return self.env['l10n_mx_edi.document']._create_update_global_invoice_document_from_invoices(self, document_values)

    def _l10n_mx_edi_cfdi_global_invoice_document_cancel_failed(self, error, cfdi, cancel_reason):
        """ Create/update the invoice document for 'cancel_failed'.

        :param error:           The error.
        :param cfdi:            The source cfdi attachment to cancel.
        :param cancel_reason:   The reason for this cancel.
        :return:                The created/updated document.
        """
        document_values = {
            'invoice_ids': [Command.set(self.ids)],
            'state': 'ginvoice_cancel_failed',
            'sat_state': None,
            'message': error,
            'attachment_id': cfdi.attachment_id.id,
            'cancellation_reason': cancel_reason,
        }
        return self.env['l10n_mx_edi.document']._create_update_global_invoice_document_from_invoices(self, document_values)

    def _l10n_mx_edi_cfdi_global_invoice_document_cancel(self, cfdi, cancel_reason):
        """ Create/update the invoice document for 'cancel'.

        :param cfdi:            The source cfdi attachment to cancel.
        :param cancel_reason:   The reason for this cancel.
        :return:                The created/updated document.
        """
        self.l10n_mx_edi_cfdi_attachment_id.ensure_one()

        document_values = {
            'invoice_ids': [Command.set(self.ids)],
            'state': 'ginvoice_cancel',
            'sat_state': 'not_defined',
            'message': None,
            'attachment_id': cfdi.attachment_id.id,
            'cancellation_reason': cancel_reason,
        }
        return self.env['l10n_mx_edi.document']._create_update_global_invoice_document_from_invoices(self, document_values)

    # -------------------------------------------------------------------------
    # CFDI: FLOWS
    # -------------------------------------------------------------------------

    def _l10n_mx_edi_cfdi_move_post_cancel(self):
        """ Cancel the current move after the document has been cancelled.
        This method is common between invoice & payment:
        """
        self.ensure_one()

        self \
            .with_context(no_new_invoice=True) \
            .message_post(body=_("The CFDI document has been successfully cancelled."))

        cfdi_values = self.env['l10n_mx_edi.document']._get_company_cfdi_values(self.company_id)
        if cfdi_values['root_company'].l10n_mx_edi_pac_test_env:
            try:
                self._check_fiscalyear_lock_date()
                self.line_ids._check_tax_lock_date()

                self.button_draft()
                self.button_cancel()
            except UserError:
                pass

    def _l10n_mx_edi_cfdi_move_update_sat_state(self, document, sat_state, error=None):
        """ Update the SAT state of the document for the current move.

        :param document:    The CFDI document to be updated.
        :param sat_state:   The newly fetched state from the SAT
        :param error:       In case of error, the message returned by the SAT.
        """
        self.ensure_one()

        document.message = None
        if sat_state == 'error' and error:
            document.message = error
            self.message_post(body=error)

        # Automatic cancel for production environment.
        if (
            self.l10n_mx_edi_cfdi_state == 'cancel'
            and self.l10n_mx_edi_cfdi_sat_state == 'cancelled'
            and self.state == 'posted'
        ):
            try:
                self._check_fiscalyear_lock_date()
                self.line_ids._check_tax_lock_date()

                self.button_draft()
                self.button_cancel()
            except UserError:
                pass

    def _l10n_mx_edi_cfdi_invoice_retry_send(self):
        """ Retry generating the PDF and CFDI for the current invoice. """
        self.ensure_one()
        option_vals = self.env['account.move.send']._get_wizard_vals_restrict_to({'l10n_mx_edi_checkbox_cfdi': True})
        move_send = self.env['account.move.send'].new(option_vals)
        self.env['account.move.send']._process_send_and_print(moves=self, wizard=move_send)

    def _l10n_mx_edi_cfdi_invoice_try_send(self):
        """ Try to generate and send the CFDI for the current invoice. """
        self.ensure_one()
        if self.state != 'posted' or self.l10n_mx_edi_cfdi_state not in (False, 'cancel', 'global_cancel'):
            return

        # == Check the config ==
        errors = self._l10n_mx_edi_cfdi_check_invoice_config()
        if errors:
            self._l10n_mx_edi_cfdi_invoice_document_sent_failed("\n".join(errors))
            return

        # == Lock ==
        self.env['l10n_mx_edi.document']._with_locked_records(self)

        # == Send ==
        def on_populate(cfdi_values):
            self._l10n_mx_edi_add_invoice_cfdi_values(cfdi_values)

        def on_failure(error, cfdi_filename=None, cfdi_str=None):
            if error == 'empty_cfdi':
                self._l10n_mx_edi_cfdi_invoice_document_empty()
            else:
                self._l10n_mx_edi_cfdi_invoice_document_sent_failed(error, cfdi_filename=cfdi_filename, cfdi_str=cfdi_str)

        def on_success(_cfdi_values, cfdi_filename, cfdi_str, populate_return=None):
            addenda = self.partner_id.l10n_mx_edi_addenda or self.commercial_partner_id.l10n_mx_edi_addenda
            if addenda:
                cfdi_str = self._l10n_mx_edi_cfdi_invoice_append_addenda(cfdi_str, addenda)

            document = self._l10n_mx_edi_cfdi_invoice_document_sent(cfdi_filename, cfdi_str)
            self \
                .with_context(no_new_invoice=True) \
                .message_post(
                    body=_("The CFDI document was successfully created and signed by the government."),
                    attachment_ids=document.attachment_id.ids,
                )

        qweb_template, _xsd_attachment_name = self.env['l10n_mx_edi.document']._get_invoice_cfdi_template()
        self.env['l10n_mx_edi.document']._send_api(
            self.company_id,
            qweb_template,
            self._l10n_mx_edi_get_invoice_cfdi_filename(),
            on_populate,
            on_failure,
            on_success,
        )

    def _l10n_mx_edi_cfdi_invoice_post_cancel(self):
        """ Cancel the current invoice and drop a message in the chatter.
        This method is only there to unify the flows since they are multiple
        ways to cancel an invoice:
        - The user can request a cancellation from Odoo.
        - The user can cancel the invoice from the SAT, then update the SAT state in Odoo.
        """
        self._l10n_mx_edi_cfdi_move_post_cancel()

    def _l10n_mx_edi_cfdi_invoice_try_cancel(self, document, cancel_reason):
        """ Try to cancel the CFDI for the current invoice.

        :param document:        The source invoice document to cancel.
        :param cancel_reason:   The reason for the cancellation.
        """
        self.ensure_one()
        if self.state != 'posted' or self.l10n_mx_edi_cfdi_state != 'sent':
            return

        # == Lock ==
        document._with_locked_records(self)

        cfdi_values = self.env['l10n_mx_edi.document']._get_company_cfdi_values(self.company_id)
        is_test_env = cfdi_values['root_company'].l10n_mx_edi_pac_test_env

        # == Cancel ==
        def on_failure(error):
            if is_test_env:
                self._l10n_mx_edi_cfdi_invoice_document_cancel_failed(error, document, cancel_reason)
            else:
                self._l10n_mx_edi_cfdi_invoice_document_cancel_requested_failed(error, document, cancel_reason)

        def on_success():
            if is_test_env:
                self._l10n_mx_edi_cfdi_invoice_document_cancel(document, cancel_reason)
            else:
                self._l10n_mx_edi_cfdi_invoice_document_cancel_requested(document, cancel_reason)
            self._l10n_mx_edi_cfdi_invoice_post_cancel()

        document._cancel_api(self.company_id, cancel_reason, on_failure, on_success)

    def _l10n_mx_edi_cfdi_invoice_update_sat_state(self, document, sat_state, error=None):
        """ Update the SAT state of the document for the current invoice.

        :param document:    The CFDI document to be updated.
        :param sat_state:   The newly fetched state from the SAT
        :param error:       In case of error, the message returned by the SAT.
        """
        self.ensure_one()

        # The user manually cancelled the document in the SAT portal.
        if document.state == 'invoice_sent' and sat_state == 'cancelled':
            if document.sat_state not in ('valid', 'cancelled', 'skip'):
                document.sat_state = 'skip'

            document = self._l10n_mx_edi_cfdi_invoice_document_cancel(
                document,
                CANCELLATION_REASON_SELECTION[1][0],  # Force '02'.
            )
            document.sat_state = sat_state
            self._l10n_mx_edi_cfdi_invoice_post_cancel()

        # The cancellation request has been approved by the SAT.
        elif document.state == 'invoice_cancel_requested' and sat_state == 'cancelled':
            document.sat_state = sat_state
            document = self._l10n_mx_edi_cfdi_invoice_document_cancel(
                document,
                document.cancellation_reason,
            )
            document.sat_state = 'cancelled'
            self._l10n_mx_edi_cfdi_invoice_post_cancel()

        else:
            document.sat_state = sat_state

        self._l10n_mx_edi_cfdi_move_update_sat_state(document, sat_state, error=error)

    def _l10n_mx_edi_cfdi_invoice_get_reconciled_payments_values(self):
        """ Compute the residual amounts before/after each payment reconciled with the current invoices.

        :return: A mapping invoice => dictionary containing:
            * payment:                  The account.move of the payment.
            * reconciled_amount:        The reconciled amount.
            * amount_residual_before:   The residual amount before reconciliation.
            * amount_residual_after:    The residual_amount after reconciliation.
        """
        # Only consider the invoices already signed.
        invoices = self.filtered(lambda x: x.is_invoice() and x.l10n_mx_edi_cfdi_state == 'sent').sorted()

        # Collect the reconciled amounts.
        reconciliation_values = {}
        for invoice in invoices:
            pay_rec_lines = invoice.line_ids\
                .filtered(lambda line: line.account_type in ('asset_receivable', 'liability_payable'))
            exchange_move_map = {}
            reconciliation_values[invoice] = {
                'payments': defaultdict(lambda: {
                    'invoice_amount_currency': 0.0,
                    'balance': 0.0,
                    'invoice_exchange_balance': 0.0,
                    'payment_amount_currency': 0.0,
                }),
            }
            for field1, field2 in (('credit', 'debit'), ('debit', 'credit')):
                for partial in pay_rec_lines[f'matched_{field1}_ids'].sorted(lambda x: not x.exchange_move_id):
                    counterpart_line = partial[f'{field1}_move_id']
                    counterpart_move = counterpart_line.move_id

                    if partial.exchange_move_id:
                        exchange_move_map[partial.exchange_move_id] = counterpart_move

                    if counterpart_move._l10n_mx_edi_is_cfdi_payment():
                        pay_results = reconciliation_values[invoice]['payments'][counterpart_move]
                        pay_results['invoice_amount_currency'] += partial[f'{field2}_amount_currency']
                        pay_results['payment_amount_currency'] += partial[f'{field1}_amount_currency']
                        pay_results['balance'] += partial.amount
                    elif counterpart_move in exchange_move_map:
                        pay_results = reconciliation_values[invoice]['payments'][exchange_move_map[counterpart_move]]
                        pay_results['invoice_exchange_balance'] += partial.amount

        # Compute the chain of payments.
        results = {}
        for invoice, invoice_values in reconciliation_values.items():
            payment_values = invoice_values['payments']
            invoice_results = results[invoice] = []
            residual = invoice.amount_total
            for pay, pay_results in sorted(list(payment_values.items()), key=lambda x: x[0].date):
                reconciled_invoice_amount = pay_results['invoice_amount_currency']
                if invoice.currency_id == invoice.company_currency_id:
                    reconciled_invoice_amount += pay_results['invoice_exchange_balance']
                invoice_results.append({
                    **pay_results,
                    'payment': pay,
                    'invoice': invoice,
                    'number_of_payments': len(payment_values),
                    'reconciled_amount': reconciled_invoice_amount,
                    'amount_residual_before': residual,
                    'amount_residual_after': residual - reconciled_invoice_amount,
                })
                residual -= reconciled_invoice_amount

        return results

    def _l10n_mx_edi_cfdi_payment_get_reconciled_invoice_values(self):
        """ Compute the amounts to send to the PAC from the current payments.

        :return: A mapping payment => dictionary containing:
            * invoices:         The reconciled invoices.
            * invoice_results:  A list of payment values, see '_l10n_mx_edi_cfdi_invoice_get_reconciled_payments_values'.
        """
        # Find all invoices linked to the current payments.
        results = {}
        payments = self.filtered(lambda x: x._l10n_mx_edi_is_cfdi_payment() and x.l10n_mx_edi_cfdi_state != 'cancel')
        all_invoices = self.env['account.move']
        exchange_move_map = {}
        exchange_move_balances = defaultdict(lambda: defaultdict(lambda: 0.0))
        for payment in payments:
            # Only the fully reconciled payments need to be sent.
            pay_rec_lines = payment.line_ids\
                .filtered(lambda line: line.account_type in ('asset_receivable', 'liability_payable'))
            if any(not x.reconciled for x in pay_rec_lines):
                continue

            # The payments must only be sent when all reconciled invoices are sent.
            skip = False
            invoices = self.env['account.move']
            for field in ('debit', 'credit'):
                for partial in pay_rec_lines[f'matched_{field}_ids'].sorted(lambda x: not x.exchange_move_id):
                    counterpart_line = partial[f'{field}_move_id']
                    counterpart_move = counterpart_line.move_id

                    if counterpart_move in exchange_move_map:
                        exchange_move_balances[payment][exchange_move_map[counterpart_move]] += partial.amount
                        continue

                    if not counterpart_move.is_invoice() or not counterpart_move.l10n_mx_edi_cfdi_state:
                        skip = True
                        break

                    if partial.exchange_move_id:
                        exchange_move_map[partial.exchange_move_id] = counterpart_move

                    invoices |= counterpart_move

            if skip:
                continue

            all_invoices |= invoices

            reconciled_amls = pay_rec_lines.matched_debit_ids.debit_move_id \
                              + pay_rec_lines.matched_credit_ids.credit_move_id
            invoices = reconciled_amls.move_id.filtered(lambda x: x.l10n_mx_edi_is_cfdi_needed and x.is_invoice())
            if any(
                not invoice.l10n_mx_edi_cfdi_state or invoice.l10n_mx_edi_cfdi_customer_rfc == 'XAXX010101000'
                for invoice in invoices
            ):
                continue

            all_invoices |= invoices
            results[payment] = {
                'invoices': invoices,
                'invoice_results': [],
            }

        # Compute the amounts to send for each invoice.
        reconciled_invoice_values = all_invoices._l10n_mx_edi_cfdi_invoice_get_reconciled_payments_values()
        for invoice, pay_results_list in reconciled_invoice_values.items():
            for pay_results in pay_results_list:
                payment = pay_results['payment']
                if payment not in results:
                    continue

                pay_results['payment_exchange_balance'] = exchange_move_balances[payment][invoice]

                results[payment]['invoice_results'].append(pay_results)

        return results

    def l10n_mx_edi_cfdi_invoice_try_update_payment(self, pay_results, force_cfdi=False):
        """ Update the CFDI state of the current payment.

        :param pay_results: The amounts to consider for each invoice.
                            See '_l10n_mx_edi_cfdi_payment_get_reconciled_invoice_values'.
        :param force_cfdi:  Force the sending of the CFDI if the payment is PUE.
        """
        self.ensure_one()

        last_document = self.l10n_mx_edi_payment_document_ids.sorted()[:1]
        invoices = pay_results['invoices']

        # == Check PUE/PPD ==
        if (
            not last_document
            and not force_cfdi
            and 'PPD' not in set(invoices.mapped('l10n_mx_edi_payment_policy'))
        ):
            self._l10n_mx_edi_cfdi_payment_document_sent_pue(invoices)
            return

        # == Retry a cancellation flow ==
        if last_document.state == 'payment_cancel_failed':
            last_document._action_retry_payment_try_cancel()
            return

        qweb_template = self.env['l10n_mx_edi.document']._get_payment_cfdi_template()

        # == Lock ==
        self.env['l10n_mx_edi.document']._with_locked_records(self + invoices)

        # == Send ==
        def on_populate(cfdi_values):
            self._l10n_mx_edi_add_payment_cfdi_values(cfdi_values, pay_results)

        def on_failure(error, cfdi_filename=None, cfdi_str=None):
            self._l10n_mx_edi_cfdi_payment_document_sent_failed(error, invoices, cfdi_filename=cfdi_filename, cfdi_str=cfdi_str)

        def on_success(_cfdi_values, cfdi_filename, cfdi_str, populate_return=None):
            self._l10n_mx_edi_cfdi_payment_document_sent(invoices, cfdi_filename, cfdi_str)

        cfdi_filename = f'{self.journal_id.code}-{self.name}-MX-Payment-20.xml'.replace('/', '')
        self.env['l10n_mx_edi.document']._send_api(
            self.company_id,
            qweb_template,
            cfdi_filename,
            on_populate,
            on_failure,
            on_success,
        )

    def _l10n_mx_edi_cfdi_payment_post_cancel(self):
        """ Cancel the current payment and drop a message in the chatter.
        This method is only there to unify the flows since they are multiple
        ways to cancel a payment:
        - The user can request a cancellation from Odoo.
        - The user can cancel the payment from the SAT, then update the SAT state in Odoo.
        """
        self._l10n_mx_edi_cfdi_move_post_cancel()

    def _l10n_mx_edi_cfdi_invoice_try_cancel_payment(self, document):
        """ Cancel the CFDI payment document passed as parameter

        :param document: The source payment document to cancel.
        """
        self.ensure_one()
        substitution_doc = document._get_substitution_document()
        cancel_uuid = substitution_doc.attachment_uuid
        cancel_reason = '01' if cancel_uuid else '02'

        # == Lock ==
        self.env['l10n_mx_edi.document']._with_locked_records(self + document.invoice_ids)

        # == Cancel ==
        def on_failure(error):
            self._l10n_mx_edi_cfdi_payment_document_cancel_failed(error, document, cancel_reason)

        def on_success():
            self._l10n_mx_edi_cfdi_payment_document_cancel(document, cancel_reason)
            self._l10n_mx_edi_cfdi_payment_post_cancel()

        document._cancel_api(self.company_id, cancel_reason, on_failure, on_success)

    def _l10n_mx_edi_cfdi_invoice_get_payments_diff(self):
        results = {
            'to_remove': defaultdict(list),
            'to_process': [],
            'need_update': set(),
        }

        # Find the payments reconciled with the current invoices.
        reconciled_invoice_values = self._l10n_mx_edi_cfdi_invoice_get_reconciled_payments_values()

        # Collect the reconciled invoices for each payment that have been sent to the SAT.
        sat_sent_payments = defaultdict(set)

        # All payments currently reconciled with the current invoices.
        all_payments = self.env['account.move']
        for invoice, pay_results_list in reconciled_invoice_values.items():
            payments = self.env['account.move']
            for pay_results in pay_results_list:
                payments |= pay_results['payment']
            all_payments |= payments

            commands = []
            for doc in invoice.l10n_mx_edi_invoice_document_ids:
                # Collect the payments that are no longer reconciled with the invoices.
                if (
                    doc.state.startswith('payment_')
                    and doc.state not in ('payment_sent', 'payment_cancel')
                    and doc.move_id not in payments
                ):
                    commands.append(Command.delete(doc.id))

                # Track the payment previously sent to the SAT.
                if doc.move_id not in sat_sent_payments and doc.state in ('payment_sent', 'payment_sent_pue', 'payment_cancel'):
                    sat_sent_payments[doc.move_id] = set(doc.invoice_ids)
            if commands:
                results['to_remove'][invoice] = commands

        # Update the payments.
        reconciled_payment_values = all_payments._l10n_mx_edi_cfdi_payment_get_reconciled_invoice_values()
        for payment, pay_results in reconciled_payment_values.items():
            last_document = payment.l10n_mx_edi_payment_document_ids.sorted()[:1]
            invoices = pay_results['invoices']

            if last_document.state == 'payment_sent_pue':
                continue

            # Check if a reconciliation is missing.
            if set(invoices) != sat_sent_payments[payment]:
                for invoice in sat_sent_payments[payment]:
                    results['need_update'].add(invoice)

            # Check if something changed in the already sent payment.
            if last_document.state == 'payment_sent':
                current_uuids = set(invoices.mapped('l10n_mx_edi_cfdi_uuid'))
                previous_uuids = set()
                if not last_document.attachment_id.raw:
                    _logger.warning(
                        "Payment document (id %s) has an empty attachment (id %s)",
                        last_document.id,
                        last_document.attachment_id.id,
                    )
                    continue
                cfdi_node = etree.fromstring(last_document.attachment_id.raw)
                for node in cfdi_node.xpath("//*[local-name()='DoctoRelacionado']"):
                    previous_uuids.add(node.attrib['IdDocumento'])
                if current_uuids == previous_uuids:
                    continue

            results['to_process'].append((payment, pay_results))

        return results

    def l10n_mx_edi_cfdi_invoice_try_update_payments(self):
        """ Try to update the state of payments for the current invoices. """
        payments_diff = self._l10n_mx_edi_cfdi_invoice_get_payments_diff()

        # Cleanup the payments that are no longer reconciled with the invoices.
        for invoice, commands in payments_diff['to_remove'].items():
            invoice.l10n_mx_edi_invoice_document_ids = commands

        # Update the payments.
        for payment, pay_results in payments_diff['to_process']:
            payment.l10n_mx_edi_cfdi_invoice_try_update_payment(pay_results)

    def _l10n_mx_edi_cfdi_payment_try_send(self, force_cfdi=False):
        """ Force the sending of the current payment.

        :param force_cfdi: Force the sending of the payment, even if the payment is PUE.
        """
        self.ensure_one()
        reconciled_payment_values = self._l10n_mx_edi_cfdi_payment_get_reconciled_invoice_values()
        for payment, pay_results in reconciled_payment_values.items():
            payment.l10n_mx_edi_cfdi_invoice_try_update_payment(pay_results, force_cfdi=force_cfdi)

    def _l10n_mx_edi_cfdi_payment_update_sat_state(self, document, sat_state, error=None):
        """ Update the SAT state of the document for the current payment.

        :param document:    The CFDI document to be updated.
        :param sat_state:   The newly fetched state from the SAT
        :param error:       In case of error, the message returned by the SAT.
        """
        self.ensure_one()

        # The user manually cancelled the document in the SAT portal.
        if document.state == 'payment_sent' and sat_state == 'cancelled':
            if document.sat_state not in ('valid', 'cancelled', 'skip'):
                document.sat_state = 'skip'

            document = self._l10n_mx_edi_cfdi_payment_document_cancel(
                document,
                CANCELLATION_REASON_SELECTION[1][0],  # Force '02'.
            )
            document.sat_state = sat_state
            self._l10n_mx_edi_cfdi_payment_post_cancel()

        else:
            document.sat_state = sat_state

        self._l10n_mx_edi_cfdi_move_update_sat_state(document, sat_state, error=error)

    def l10n_mx_edi_cfdi_payment_force_try_send(self):
        self._l10n_mx_edi_cfdi_payment_try_send(force_cfdi=True)

    def _l10n_mx_edi_cfdi_global_invoice_try_send(self, periodicity='04', origin=None):
        """ Create a CFDI global invoice for multiple invoices.

        :param periodicity:     The value to fill the 'Periodicidad' value.
        :param origin:          The origin of the GI when cancelling an existing one.
        """
        cfdi_date = fields.Date.context_today(self)

        invoices = self._l10n_mx_edi_check_invoices_for_global_invoice(origin=origin)

        # == Check the config ==
        errors = []
        for invoice in invoices:
            errors += invoice._l10n_mx_edi_cfdi_check_invoice_config()
        if errors:
            invoices._l10n_mx_edi_cfdi_global_invoice_document_sent_failed("\n".join(set(errors)))
            return

        # == Lock ==
        self.env['l10n_mx_edi.document']._with_locked_records(invoices)

        # == Send ==
        def on_populate(cfdi_values):
            invoices_per_error = defaultdict(lambda: self.env['account.move'])
            inv_cfdi_values_list = []
            for invoice in invoices:

                # The refund are managed by the invoice.
                if invoice.reversed_entry_id:
                    continue

                inv_cfdi_values = dict(cfdi_values)
                invoice._l10n_mx_edi_add_invoice_cfdi_values(inv_cfdi_values, global_invoice=True)

                inv_errors = inv_cfdi_values.get('errors')
                if inv_errors:
                    for error in inv_cfdi_values['errors']:

                        # The invoice is empty. Skip it.
                        if error == 'empty_cfdi':
                            break

                        invoices_per_error[error] |= invoice
                else:
                    inv_cfdi_values_list.append(inv_cfdi_values)

            if invoices_per_error:
                errors = []
                for error, invoices_in_error in invoices_per_error.items():
                    invoices_str = ",".join(invoices_in_error.mapped('name'))
                    errors.append(_("On %s: %s", invoices_str, error))
                cfdi_values['errors'] = errors
                return

            # The global invoice is empty.
            if not inv_cfdi_values_list:
                cfdi_values['errors'] = ['empty_cfdi']
                return

            cfdi_values.update(
                **self.env['l10n_mx_edi.document']._get_global_invoice_cfdi_values(
                    inv_cfdi_values_list,
                    cfdi_date,
                    periodicity=periodicity,
                    origin=origin,
                )
            )

            self.env['l10n_mx_edi.document']._with_locked_records(cfdi_values['sequence'])
            return cfdi_values['sequence']

        def on_failure(error, cfdi_filename=None, cfdi_str=None):
            if error == 'empty_cfdi':
                self._l10n_mx_edi_cfdi_global_invoice_document_empty()
            else:
                self._l10n_mx_edi_cfdi_global_invoice_document_sent_failed(error, cfdi_filename=cfdi_filename, cfdi_str=cfdi_str)

        def on_success(cfdi_values, cfdi_filename, cfdi_str, populate_return=None):
            # Consume the next sequence number.
            self.env['l10n_mx_edi.document']._consume_global_invoice_cfdi_sequence(populate_return, int(cfdi_values['folio']))

            # Create the document.
            document = self._l10n_mx_edi_cfdi_global_invoice_document_sent(cfdi_filename, cfdi_str)

            # Chatters.
            for invoice in self:
                invoice \
                    .with_context(no_new_invoice=True) \
                    .message_post(
                    body=_("The Global CFDI document was successfully created and signed by the government."),
                    attachment_ids=document.attachment_id.ids,
                )

        qweb_template, _xsd_attachment_name = self.env['l10n_mx_edi.document']._get_invoice_cfdi_template()
        cfdi_filename = f"{self.journal_id.code}-MX-Global-Invoice-4.0.xml".replace('/', '')
        self.env['l10n_mx_edi.document']._send_api(
            self.company_id,
            qweb_template,
            cfdi_filename,
            on_populate,
            on_failure,
            on_success,
        )

    def _l10n_mx_edi_cfdi_global_invoice_post_cancel(self):
        """ Cancel the current payment and drop a message in the chatter.
        This method is only there to unify the flows since they are multiple
        ways to cancel a payment:
        - The user can request a cancellation from Odoo.
        - The user can cancel the payment from the SAT, then update the SAT state in Odoo.
        """

        for record in self:
            record \
                .with_context(no_new_invoice=True) \
                .message_post(body=_("The Global CFDI document has been successfully cancelled."))

    def _l10n_mx_edi_cfdi_global_invoice_try_cancel(self, document, cancel_reason):
        """ Create a CFDI global invoice for multiple invoices.

        :param document:        The Global invoice document to cancel.
        :param cancel_reason:   The reason for the cancellation.
        """
        # == Lock ==
        document._with_locked_records(self)

        # == Cancel ==
        def on_failure(error):
            self._l10n_mx_edi_cfdi_global_invoice_document_cancel_failed(error, document, cancel_reason)

        def on_success():
            self._l10n_mx_edi_cfdi_global_invoice_document_cancel(document, cancel_reason)
            self._l10n_mx_edi_cfdi_global_invoice_post_cancel()

        document._cancel_api(self.company_id, cancel_reason, on_failure, on_success)

    def _l10n_mx_edi_cfdi_global_invoice_update_document_sat_state(self, document, sat_state, error=None):
        """ Update the SAT state of the document for the current global invoice.

        :param document:    The CFDI document to be updated.
        :param sat_state:   The newly fetched state from the SAT
        :param error:       In case of error, the message returned by the SAT.
        """
        # The user manually cancelled the document in the SAT portal.
        if document.state == 'ginvoice_sent' and sat_state == 'cancelled':
            if document.sat_state not in ('valid', 'cancelled', 'skip'):
                document.sat_state = 'skip'

            document = self._l10n_mx_edi_cfdi_global_invoice_document_cancel(
                document,
                CANCELLATION_REASON_SELECTION[1][0],  # Force '02'.
            )
            document.sat_state = sat_state
            self._l10n_mx_edi_cfdi_global_invoice_post_cancel()
        else:
            document.sat_state = sat_state

        document.message = None
        if sat_state == 'error' and error:
            document.message = error
            self.invoice_ids._message_log_batch(bodies={invoice.id: error for invoice in self.invoice_ids})

    def l10n_mx_edi_action_create_global_invoice(self):
        """ Action to open the wizard allowing to create a global invoice CFDI document for the
        selected invoices.

        :return: An action to open the wizard.
        """
        return {
            'name': _("Create Global Invoice"),
            'type': 'ir.actions.act_window',
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'l10n_mx_edi.global_invoice.create',
            'target': 'new',
            'context': {'default_move_ids': [Command.set(self.ids)]},
        }

    def l10n_mx_edi_cfdi_try_sat(self):
        self.ensure_one()
        if self.is_invoice():
            documents = self.l10n_mx_edi_invoice_document_ids
        elif self._l10n_mx_edi_is_cfdi_payment():
            documents = self.l10n_mx_edi_payment_document_ids
        else:
            return

        for document in documents.filtered_domain(documents._get_update_sat_status_domain(from_cron=False)):
            document._update_sat_state()

    # -------------------------------------------------------------------------
    # CFDI: IMPORT
    # -------------------------------------------------------------------------

    @api.model
    def _l10n_mx_edi_import_cfdi_get_tax_from_node(self, tax_node, line, is_withholding=False):
        tax_type = CFDI_CODE_TO_TAX_TYPE.get(tax_node.attrib.get('Impuesto'))
        tasa_o_cuota = tax_node.attrib.get('TasaOCuota')
        if not tasa_o_cuota:
            self.message_post(body=_("Tax ID %s can not be imported", tax_type))
            return False
        else:
            amount = float(tasa_o_cuota) * (-100 if is_withholding else 100)
            domain = [
                *self.env['account.journal']._check_company_domain(line.company_id),
                ('amount', '=', amount),
                ('type_tax_use', '=', 'sale' if self.journal_id.type == 'sale' else 'purchase'),
                ('amount_type', '=', 'percent'),
            ]

            if tax_type:
                domain.append(('l10n_mx_tax_type', '=', tax_type))
            taxes = self.env['account.tax'].search(domain, limit=2)
            if len(taxes) != 1:
                line.move_id.to_check = True
            if not taxes:
                msg = _('Could not retrieve the %s tax with rate %s%%.', tax_type, amount)
                msg_wh = _('Could not retrieve the %s withholding tax with rate %s%%.', tax_type, amount)
                line.move_id.message_post(body=msg_wh if is_withholding else msg)
            return taxes[:1]

    def _l10n_mx_edi_import_cfdi_fill_invoice_line(self, tree, line):
        # Product
        code = tree.attrib.get('NoIdentificacion')  # default_code if export from Odoo
        unspsc_code = tree.attrib.get('ClaveProdServ')  # UNSPSC code
        description = tree.attrib.get('Descripcion')  # label of the invoice line "[{p.default_code}] {p.name}"
        cleaned_name = re.sub(r"^\[.*\] ", "", description)
        product = self.env['product.product']._retrieve_product(
            name=cleaned_name,
            default_code=code,
            extra_domain=[('unspsc_code_id.code', '=', unspsc_code)],
            company=self.company_id,
        )
        if not product:
            product = self.env['product.product']._retrieve_product(name=cleaned_name, default_code=code)
        line.product_id = product

        # Taxes
        tax_ids = []
        for tax_node in tree.findall("{*}Impuestos/{*}Traslados/{*}Traslado"):
            tax = self._l10n_mx_edi_import_cfdi_get_tax_from_node(tax_node, line)
            if tax:
                tax_ids.append(tax.id)
            tax_type = CFDI_CODE_TO_TAX_TYPE.get(tax_node.attrib.get('Impuesto'))
            tasa_o_cuota = tax_node.attrib.get('TasaOCuota')
            tipo_factor = tax_node.attrib.get('TipoFactor')
            if not tasa_o_cuota and tipo_factor != "Exento":
                self.message_post(body=_("Tax ID %s can not be imported", tax_type))
            else:
                amount = float(tasa_o_cuota) * 100 if tipo_factor != "Exento" else 0
                domain = [
                    *self.env['account.journal']._check_company_domain(line.company_id),
                    ('amount', '=', amount),
                    ('type_tax_use', '=', 'sale' if self.journal_id.type == 'sale' else 'purchase'),
                    ('amount_type', '=', 'percent'),
                ]
                tax_group = self.env.ref(f'account.{line.company_id.id}_tax_group_exe_0', raise_if_not_found=False)
                if tax_group and tipo_factor == 'Exento':
                    domain.append(('tax_group_id', '=', tax_group.id))
                if tax_type:
                    domain.append(('repartition_line_ids.tag_ids.name', '=', tax_type))
                tax = self.env['account.tax'].search(domain, limit=1)
                if not tax:
                    # try without again without using the tags: some are IVA but only have 'DIOT' tags
                    domain.pop()
                    tax = self.env['account.tax'].search(domain, limit=1)
                if tax:
                    tax_ids.append(tax.id)
                elif tax_type:
                    line.move_id.message_post(body=_("Could not retrieve the %s tax with rate %s%%.", tax_type, amount))
                else:
                    line.move_id.message_post(body=_("Could not retrieve the tax with rate %s%%.", amount))

        # Withholding Taxes
        for wh_tax_node in tree.findall("{*}Impuestos/{*}Retenciones/{*}Retencion"):
            wh_tax = self._l10n_mx_edi_import_cfdi_get_tax_from_node(wh_tax_node, line, is_withholding=True)
            if wh_tax:
                tax_ids.append(wh_tax.id)

        # Discount
        discount_percent = 0
        discount_amount = float(tree.attrib.get('Descuento') or 0)
        gross_price_subtotal_before_discount = float(tree.attrib.get('Importe'))
        if not self.currency_id.is_zero(discount_amount):
            discount_percent = (discount_amount/gross_price_subtotal_before_discount)*100

        line.write({
            'quantity': float(tree.attrib.get('Cantidad')),
            'price_unit': float(tree.attrib.get('ValorUnitario')),
            'discount': discount_percent,
            'tax_ids': [Command.set(tax_ids)],
        })
        return True

    def _l10n_mx_edi_import_cfdi_fill_partner(self, tree):
        outgoing_invoice = self.journal_id.type == 'sale'
        role = "Receptor" if outgoing_invoice else "Emisor"
        partner_node = tree.find("{*}" + role)
        rfc = partner_node.attrib.get('Rfc')
        name = partner_node.attrib.get('Nombre')
        partner = self.partner_id._retrieve_partner(
            name=name,
            vat=rfc,
            company=self.company_id,
        )
        # create a partner if it's not found
        if not partner:
            is_foreign_partner = rfc == 'XEXX010101000'
            partner_vals = {
                'name': name,
                'country_id': not is_foreign_partner and self.env.ref('base.mx').id,
            }
            if not (is_foreign_partner or rfc == 'XAXX010101000'):
                partner_vals['vat'] = rfc
                if outgoing_invoice:
                    zip_code = partner_node.attrib.get('DomicilioFiscalReceptor')
                    partner_vals['zip'] = zip_code
            elif is_foreign_partner:
                export_fiscal_position = self.company_id._l10n_mx_edi_get_foreign_customer_fiscal_position()
                if export_fiscal_position:
                    partner_vals['property_account_position_id'] = export_fiscal_position.id
            partner = self.env['res.partner'].create(partner_vals)
        return partner

    def _l10n_mx_edi_import_cfdi_fill_invoice(self, tree):
        # Partner
        cfdi_vals = self.env['l10n_mx_edi.document']._decode_cfdi_attachment(etree.tostring(tree))
        partner = self._l10n_mx_edi_import_cfdi_fill_partner(tree)
        if not partner:
            return
        self.partner_id = partner
        # Payment way
        forma_pago = tree.attrib.get('FormaPago')
        self.l10n_mx_edi_payment_method_id = self.env['l10n_mx_edi.payment.method'].search(
            [('code', '=', forma_pago)], limit=1)
        # Payment policy
        self.l10n_mx_edi_payment_policy = tree.attrib.get('MetodoPago')
        # Usage
        usage = cfdi_vals['usage']
        if usage in dict(self._fields['l10n_mx_edi_usage'].selection):
            self.l10n_mx_edi_usage = usage
        # Invoice date
        date = cfdi_vals['stamp_date'] or cfdi_vals['emission_date_str']
        if date:
            self.invoice_date = datetime.strptime(date, '%Y-%m-%d %H:%M:%S').date()
        # Currency
        currency_name = tree.attrib.get('Moneda')
        currency = self.env['res.currency'].search([('name', '=', currency_name)], limit=1)
        if currency:
            self.currency_id = currency
        # Fiscal folio
        self.l10n_mx_edi_cfdi_uuid = cfdi_vals['uuid']
        # Lines
        for invl_el in tree.findall("{*}Conceptos/{*}Concepto"):
            line = self.invoice_line_ids.create({'move_id': self.id, 'company_id': self.company_id.id})
            self._l10n_mx_edi_import_cfdi_fill_invoice_line(invl_el, line)
        return True

    def _l10n_mx_edi_import_cfdi_invoice(self, invoice, file_data, new=False):
        invoice.ensure_one()
        if invoice.l10n_mx_edi_cfdi_attachment_id:
            # invoice is already associated with a CFDI document, do nothing
            return False
        tree = file_data['xml_tree']
        # handle payments
        if tree.findall('.//{*}Pagos'):
            invoice.message_post(body=_("Importing a CFDI Payment is not supported."))
            return
        move_type = 'refund' if tree.attrib.get('TipoDeComprobante') == 'E' else 'invoice'
        if invoice.journal_id.type == 'sale':
            move_type = 'out_' + move_type
        elif invoice.journal_id.type == 'purchase':
            move_type = 'in_' + move_type
        else:
            return
        invoice.move_type = move_type
        if not invoice.invoice_line_ids:
            # don't fill the invoice if it already has lines, simply give it the cfdi info
            invoice._l10n_mx_edi_import_cfdi_fill_invoice(tree)
        # create the document
        self.env['l10n_mx_edi.document'].create({
            'move_id': invoice.id,
            'invoice_ids': [Command.set(invoice.ids)],
            'state': 'invoice_sent' if invoice.is_sale_document() else 'invoice_received',
            'sat_state': 'not_defined',
            'attachment_id': file_data['attachment'].id,
            'datetime': fields.Datetime.now(),
        })
        return True

    def _get_edi_decoder(self, file_data, new=False):
        # EXTENDS 'account'
        if file_data.get('is_cfdi', False):
            return self._l10n_mx_edi_import_cfdi_invoice
        return super()._get_edi_decoder(file_data, new=new)
