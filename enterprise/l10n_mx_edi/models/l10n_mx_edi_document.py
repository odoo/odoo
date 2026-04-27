# -*- coding: utf-8 -*-
import base64
import json
import random
import re

import requests
import string

from collections import defaultdict
from datetime import datetime, time, timedelta
from json.decoder import JSONDecodeError
from lxml import etree
from odoo.tools.zeep import Client, Transport
from pytz import timezone

from odoo import _, api, models, modules, fields, tools, SUPERUSER_ID
from odoo.exceptions import UserError
from odoo.osv import expression
from odoo.tools.float_utils import float_is_zero, float_round

CFDI_DATE_FORMAT = '%Y-%m-%dT%H:%M:%S'
CANCELLATION_REASON_SELECTION = [
    ('01', "01 - Document issued with errors (with related document)"),
    ('02', "02 - Document issued with errors (no replacement)"),
    ('03', "03 - The operation was not carried out"),
    ('04', "04 - Nominative operation related to the global invoice"),
]

CANCELLATION_REASON_DESCRIPTION = (
    f"{CANCELLATION_REASON_SELECTION[0][1]}.\n"
    "This option applies when there is an error in the document data, so it must be reissued. In this case, the replacement document is"
    " referenced in the cancellation request.\n"
    f"{CANCELLATION_REASON_SELECTION[1][1]}.\n"
    "This option applies when there is an error in the document data and no replacement document will be generated.\n"
    f"{CANCELLATION_REASON_SELECTION[2][1]}.\n"
    "This option applies when a transaction was invoiced that does not materialize.\n"
    f"{CANCELLATION_REASON_SELECTION[3][1]}.\n"
    "This option applies when a sale was included in the global invoice of operations with the general public, but should actually be"
    " excluded since the partner has requested a CFDI to be issued in their name.\n"
)

GLOBAL_INVOICE_PERIODICITY_DEFAULT_VALUES = {
    'selection': [
        ('01', "Daily"),
        ('02', "Weekly"),
        ('03', "Fortnightly"),
        ('04', "Monthly"),
        ('05', "Bimonthly"),
    ],
    'default': '04',
    'string': "Periodicity",
    'help': "The periodicity at which you want to send the CFDI global invoices.",
}

TAX_TYPE_TO_CFDI_CODE = {'isr': '001', 'iva': '002', 'ieps': '003'}
CFDI_CODE_TO_TAX_TYPE = {v: k for k, v in TAX_TYPE_TO_CFDI_CODE.items()}

USAGE_SELECTION = [
    ('G01', 'Acquisition of merchandise'),
    ('G02', 'Returns, discounts or bonuses'),
    ('G03', 'General expenses'),
    ('I01', 'Constructions'),
    ('I02', 'Office furniture and equipment investment'),
    ('I03', 'Transportation equipment'),
    ('I04', 'Computer equipment and accessories'),
    ('I05', 'Dices, dies, molds, matrices and tooling'),
    ('I06', 'Telephone communications'),
    ('I07', 'Satellite communications'),
    ('I08', 'Other machinery and equipment'),
    ('D01', 'Medical, dental and hospital expenses.'),
    ('D02', 'Medical expenses for disability'),
    ('D03', 'Funeral expenses'),
    ('D04', 'Donations'),
    ('D05', 'Real interest effectively paid for mortgage loans (room house)'),
    ('D06', 'Voluntary contributions to SAR'),
    ('D07', 'Medical insurance premiums'),
    ('D08', 'Mandatory School Transportation Expenses'),
    ('D09', 'Deposits in savings accounts, premiums based on pension plans.'),
    ('D10', 'Payments for educational services (Colegiatura)'),
    ('S01', "Without fiscal effects"),
]


class L10nMxEdiDocument(models.Model):
    _name = 'l10n_mx_edi.document'
    _description = "Mexican documents that needs to transit outside of Odoo"
    _order = 'datetime DESC, id DESC'

    invoice_ids = fields.Many2many(
        comodel_name='account.move',
        relation='l10n_mx_edi_invoice_document_ids_rel',
        column1='document_id',
        column2='invoice_id',
        copy=False,
        readonly=True,
    )
    datetime = fields.Datetime(required=True)
    move_id = fields.Many2one(comodel_name='account.move', auto_join=True, index='btree_not_null')
    attachment_id = fields.Many2one(comodel_name='ir.attachment')
    attachment_uuid = fields.Char(
        string="Fiscal Folio",
        compute='_compute_from_attachment',
        store=True,
    )
    attachment_origin = fields.Char(
        string="Origin",
        compute='_compute_from_attachment',
        store=True,
    )
    cancellation_reason = fields.Selection(
        selection=CANCELLATION_REASON_SELECTION,
        string="Cancellation Reason",
        copy=False,
        help=CANCELLATION_REASON_DESCRIPTION,
    )
    message = fields.Char(string="Info")
    state = fields.Selection(
        selection=[
            ('invoice_sent', "Sent"),
            ('invoice_sent_failed', "Send In Error"),
            ('invoice_cancel_requested', "Cancel Requested"),
            ('invoice_cancel_requested_failed', "Cancel Requested In Error"),
            ('invoice_cancel', "Cancel"),
            ('invoice_cancel_failed', "Cancel In Error"),
            ('invoice_received', "Received"),
            ('ginvoice_sent', "Sent Global"),
            ('ginvoice_sent_failed', "Send Global In Error"),
            ('ginvoice_cancel', "Cancel Global"),
            ('ginvoice_cancel_failed', "Cancel Global In Error"),
            ('payment_sent_pue', "PUE Payment"),
            ('payment_sent', "Payment Sent"),
            ('payment_sent_failed', "Payment Send In Error"),
            ('payment_cancel', "Payment Cancel"),
            ('payment_cancel_failed', "Payment Cancel In Error"),
        ],
        required=True,
    )
    sat_state = fields.Selection(
        selection=[
            ('skip', "Skip"),
            ('valid', "Validated"),
            ('cancelled', "Cancelled"),
            ('not_found', "Not Found"),
            ('not_defined', "Not Defined"),
            ('error', "Error"),
        ],
    )

    cancel_button_needed = fields.Boolean(compute='_compute_cancel_button_needed')
    retry_button_needed = fields.Boolean(compute='_compute_retry_button_needed')
    show_button_needed = fields.Boolean(compute='_compute_show_button_needed')

    # -------------------------------------------------------------------------
    # COMPUTE
    # -------------------------------------------------------------------------

    @api.depends('attachment_id.raw')
    def _compute_from_attachment(self):
        """ Decode the CFDI document and extract some valuable information such as the UUID or the origin. """
        for doc in self.with_context(bin_size=False):
            doc.attachment_uuid = None
            doc.attachment_origin = None
            if doc.attachment_id:
                cfdi_infos = self._decode_cfdi_attachment(doc.attachment_id.raw)
                if cfdi_infos:
                    doc.attachment_uuid = cfdi_infos['uuid']
                    doc.attachment_origin = cfdi_infos['origin']

    @api.model
    def _get_cancel_button_map(self):
        """ Mapping to manage the 'cancel' flow on documents.

        :return: A mapping:
            <source_state>: (<cancel_state>, <extra_condition_function>, <cancel_function>)
            where:
                <source_state>  is the original state of the document allowing a cancel flow (e.g. 'invoice_sent').
                <cancel_state>  is the state cancelling <source_state> (e.g. 'invoice_cancel').
                <extra_condition_function>  is an optional function allowing extra checking on the document (mainly specific stuff
                                            depending on the related business record owning the document).
                <cancel_function>   is the function to be called when clicking on the 'cancel' button.
        """

        def invoice_sent_cancel(doc):
            # For invoices, we support the cancellation reason 01. Then, let's delegate the cancellation flow to the wizard.
            if doc.move_id:
                return doc.action_request_cancel()

            # For others documents like pos orders, we only support the cancellation reason 02 atm.
            records = self._get_source_records()
            records._l10n_mx_edi_cfdi_invoice_try_cancel(doc, '02')

        return {
            'invoice_sent': (
                'invoice_cancel',
                lambda x: not x.move_id or x.move_id._l10n_mx_edi_need_cancel_request(),
                invoice_sent_cancel,
            ),
            'ginvoice_sent': (
                'ginvoice_cancel',
                None,
                lambda x: x.action_request_cancel(),
            ),
            'payment_sent': (
                'payment_cancel',
                None,
                lambda x: x.action_request_cancel_payment(),
            ),
        }

    @api.depends('state')
    def _compute_cancel_button_needed(self):
        """ Compute whatever or not the 'cancel' button should be displayed. """
        doc_state_mapping = self._get_cancel_button_map()
        for doc in self:
            doc.cancel_button_needed = False
            results = doc_state_mapping.get(doc.state)
            if (
                results
                and doc.sat_state not in ('cancelled', 'skip')
                and (not results[1] or results[1](doc))
            ):
                doc.cancel_button_needed = not doc._get_cancel_document_from_source()

    @api.model
    def _get_retry_button_map(self):
        """ Mapping to manage the 'retry' flow on documents.

        :return: A mapping:
            <source_state>: (<extra_condition_function>, <retry_function>)
            where:
                <source_state>  is the original state of the document allowing a retry flow
                                (a.k.a any failing document such as 'invoice_sent_failed').
                <extra_condition_function>  is an optional function allowing extra checking on the document (mainly specific stuff
                                            depending on the related business record owning the document).
                <retry_function>    is the function to be called when clicking on the 'retry' button.
        """
        return {
            'invoice_sent_failed': (
                None,
                lambda x: x._action_retry_invoice_try_send(),
            ),
            'invoice_cancel_failed': (
                None,
                lambda x: x._action_retry_invoice_try_cancel(),
            ),
            'invoice_cancel_requested_failed': (
                None,
                lambda x: x._action_retry_invoice_try_cancel(),
            ),
            'payment_sent_failed': (
                lambda x: x.move_id,
                lambda x: x.move_id._l10n_mx_edi_cfdi_payment_try_send(),
            ),
            'payment_cancel_failed': (
                None,
                lambda x: x._action_retry_payment_try_cancel(),
            ),
            'ginvoice_sent_failed': (
                lambda x: x.attachment_id,
                lambda x: x._action_retry_global_invoice_try_send(),
            ),
            'ginvoice_cancel_failed': (
                None,
                lambda x: x._action_retry_global_invoice_try_cancel(),
            ),
        }

    @api.depends('state', 'attachment_id')
    def _compute_retry_button_needed(self):
        """ Compute whatever or not the 'retry' button should be displayed. """
        doc_state_mapping = self._get_retry_button_map()
        for doc in self:
            results = doc_state_mapping.get(doc.state)
            doc.retry_button_needed = bool(results) and (not results[0] or results[0](doc))

    @api.depends('state')
    def _compute_show_button_needed(self):
        """ Compute whatever or not the 'show' button should be displayed. """
        for doc in self:
            if doc.state.startswith('payment_') and not doc.move_id:
                doc.show_button_needed = False
                continue
            doc.show_button_needed = doc.state.startswith('payment_') or doc.state.startswith('ginvoice_')

    # -------------------------------------------------------------------------
    # BUTTON ACTIONS
    # -------------------------------------------------------------------------

    @api.model
    def _can_commit(self):
        return not tools.config['test_enable'] and not modules.module.current_test

    def _get_source_records(self):
        """ Get the originator records for the current document.
        This is useful when some flows are the same across multiple input documents.

        :return: A recordset.
        """
        self.ensure_one()
        return self.invoice_ids

    def _get_source_document_from_cancel(self, target_state):
        """ Get the source document for the current cancel document.
        For example, if the current document is 'invoice_cancel' and the target_state is 'invoice_sent', this method will give you
        the source document having the 'invoice_sent' originator of this 'invoice_cancel' document.

        :param target_state: The state of the targeted document.
        :return: Another document if any.
        """
        self.ensure_one()
        if not self.attachment_id:
            return

        return self.search(
            [('state', '=', target_state), ('attachment_id', '=', self.attachment_id.id)],
            limit=1,
        )

    def _get_cancel_document_from_source(self):
        """ Get the cancel document for the current signed document.
        For example, if the current document is 'invoice_cancel' and the target_state is 'invoice_sent', this method will give you
        the source document having the 'invoice_sent' originator of this 'invoice_cancel' document.

        :return: Another document if any.
        """
        self.ensure_one()
        if not self.attachment_id:
            return

        doc_state_mapping = self._get_cancel_button_map()
        return self.search(
            [('state', '=', doc_state_mapping[self.state][0]), ('attachment_id', '=', self.attachment_id.id)],
            limit=1,
        )

    def _get_substitution_document(self):
        """ Get the document substituting the current signed document.
        This happens when using the cancellation reason 01 in which you need to replace first the CFDI document by another one
        before cancelling it. In that case, the substitution document is linked to the current one through the origin field.

        :return: Another document if any.
        """
        self.ensure_one()
        uuid = self.attachment_uuid
        if not uuid:
            return self.env['l10n_mx_edi.document']

        return self.env['l10n_mx_edi.document'].search(
            [('id', '!=', self.id), ('state', '=', self.state), ('attachment_origin', '=like', f'04|{uuid}%')],
            limit=1,
        )

    def action_show_document(self):
        """ View the record(s) owning this document. """
        self.ensure_one()
        if self.state.startswith('payment_'):
            return self.move_id.action_open_business_doc()
        elif self.state.startswith('ginvoice_'):
            return {
                'name': _("Global Invoice"),
                'type': 'ir.actions.act_window',
                'res_model': self.invoice_ids._name,
                'view_mode': 'list,form',
                'domain': [('id', 'in', self.invoice_ids.ids)],
                'context': {'create': False},
            }

    def action_download_file(self):
        """ Download the XML file linked to the document.

        :return: An action to download the attachment.
        """
        self.ensure_one()
        return {
            'type': 'ir.actions.act_url',
            'url': f'/web/content/{self.attachment_id.id}?download=true',
        }

    def action_force_payment_cfdi(self):
        """ Force the CFDI for the PUE payment document."""
        raise UserError(_("You can no longer send a CFDI for a PUE payment."))

    def action_cancel(self):
        """ Cancel the document. """
        self.ensure_one()
        return self._get_cancel_button_map()[self.state][2](self)

    def _action_retry_invoice_try_send(self):
        """ Retry the sending of an invoice CFDI document that failed to be sent. """
        self.ensure_one()
        records = self._get_source_records()
        if self.move_id:
            records._l10n_mx_edi_cfdi_invoice_retry_send()
        else:
            records._l10n_mx_edi_cfdi_invoice_try_send()

    def _action_retry_invoice_try_cancel(self):
        """ Retry the cancellation of a the invoice cfdi document that failed to be cancelled. """
        self.ensure_one()
        source_document = self._get_source_document_from_cancel('invoice_sent')
        if source_document:
            records = self._get_source_records()
            records._l10n_mx_edi_cfdi_invoice_try_cancel(source_document, self.cancellation_reason)

    def _action_retry_payment_try_cancel(self):
        """ Retry the cancellation of a the payment cfdi document that failed to be cancelled. """
        self.ensure_one()
        source_document = self._get_source_document_from_cancel('payment_sent')
        if source_document:
            self.move_id._l10n_mx_edi_cfdi_invoice_try_cancel_payment(source_document)

    def _action_retry_global_invoice_try_send(self):
        """ Retry the sending of a global invoice cfdi document that failed to be sent. """
        self.ensure_one()
        cfdi_infos = self._decode_cfdi_attachment(self.attachment_id.raw)
        if not cfdi_infos:
            return

        records = self._get_source_records()
        records._l10n_mx_edi_cfdi_global_invoice_try_send(
            periodicity=cfdi_infos['periodicity'],
            origin=self.attachment_origin,
        )

    def _action_retry_global_invoice_try_cancel(self):
        """ Retry the cancellation of a the global invoice cfdi document that failed to be cancelled. """
        self.ensure_one()
        source_document = self._get_source_document_from_cancel('ginvoice_sent')
        if source_document:
            records = self._get_source_records()
            records._l10n_mx_edi_cfdi_global_invoice_try_cancel(source_document, self.cancellation_reason)

    def action_retry(self):
        """ Retry the current document. """
        self.ensure_one()
        self._get_retry_button_map()[self.state][1](self)

    def action_request_cancel(self):
        """ Open the cancellation wizard to cancel the current document.

        :return: An action opening the 'l10n_mx_edi.invoice.cancel' wizard.
        """
        self.ensure_one()
        return {
            'name': _("Request CFDI Cancellation"),
            'type': 'ir.actions.act_window',
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'l10n_mx_edi.invoice.cancel',
            'target': 'new',
            'context': {'default_document_id': self.id},
        }

    def action_request_cancel_payment(self):
        """ Cancel the current payment document.
        """
        self.ensure_one()
        self.move_id._l10n_mx_edi_cfdi_invoice_try_cancel_payment(self)

    # -------------------------------------------------------------------------
    # CFDI: HELPERS
    # -------------------------------------------------------------------------

    @api.model
    def _get_invoice_cfdi_template(self):
        """ Hook to be overridden in case the CFDI version changes.

        :return: the qweb_template
        """
        return 'l10n_mx_edi.cfdiv40'

    @api.model
    def _get_payment_cfdi_template(self):
        """ Hook to be overridden in case the CFDI version changes.

        :return: the qweb_template
        """
        return 'l10n_mx_edi.payment20'

    @api.model
    def _cfdi_sanitize_to_legal_name(self, name):
        """ We remove the SA de CV / SL de CV / S de RL de CV as they are never in the official name in the XML.

        :param name: The name to clean.
        :return: The formatted name.
        """
        regex = r"(?i:\s+(s\.?\s?(a\.?)( de c\.?v\.?|)|(s\.?\s?(a\.?s\.?)|s\.? en c\.?( por a\.?)?|s\.?\s?c\.?\s?(l\.?(\s?\(?limitada)?\)?|s\.?(\s?\(?suplementada\)?)?)|s\.? de r\.?l\.?)))\s*$"
        return re.sub(regex, "", name or '').upper()

    @api.model
    def _add_base_cfdi_values(self, cfdi_values):
        """ Add the basic values to 'cfdi_values'.

        :param cfdi_values: The current CFDI values.
        """

        def format_string(text, size):
            """ Replace from text received the characters that are not found in the regex. This regex is taken from SAT
            documentation: https://goo.gl/C9sKH6
            Ex. 'Product ABC (small size)' - 'Product ABC small size'

            :param text: Text to format.
            :param size: The maximum size of the string
            """
            if not text:
                return None
            text = text.replace('|', ' ')
            return text.strip()[:size]

        cfdi_values.update({
            'format_string': format_string,
            'exportacion': '01',
        })

    @api.model
    def _get_company_cfdi_values(self, company):
        """ Get the company to consider when creating the CFDI document.
        The root company will be the one with configured certificates on the hierarchy.

        :param company: The res.company to consider when generating the CFDI.
        :return: A dictionary containing:
            * company:          The company of the document.
            * root_company:     The company used to interact with the SAT.
            * issued_address:   The company's address.
        """
        root_company = company.sudo().parent_ids[::-1].filtered('partner_id.vat')[:1] or company

        cfdi_values = {
            'company': company,
            'issued_address': company.partner_id.commercial_partner_id,
            'root_company': root_company,
        }

        if root_company.l10n_mx_edi_pac:
            pac_test_env = root_company.l10n_mx_edi_pac_test_env
            pac_password = root_company.sudo().l10n_mx_edi_pac_password
            if not pac_test_env and not pac_password:
                cfdi_values['errors'] = [_("No PAC credentials specified.")]
        else:
            cfdi_values['errors'] = [_("No PAC specified.")]

        return cfdi_values

    @api.model
    def _add_certificate_cfdi_values(self, cfdi_values):
        """ Add the values about the certificate to 'cfdi_values'.

        :param cfdi_values: The current CFDI values.
        """
        company = cfdi_values['company']
        root_company = cfdi_values['root_company']
        certificate_sudo = company.sudo().l10n_mx_edi_certificate_ids.filtered('is_valid')[:1]
        if not certificate_sudo and company != root_company:
            certificate_sudo = root_company.sudo().l10n_mx_edi_certificate_ids.filtered('is_valid')[:1]
        if not certificate_sudo:
            cfdi_values['errors'] = [_("No valid certificate found")]
            return

        supplier = root_company.partner_id.commercial_partner_id.with_user(self.env.user)
        fiscal_regime = company.l10n_mx_edi_fiscal_regime or root_company.l10n_mx_edi_fiscal_regime

        cfdi_values.update({
            'certificate': certificate_sudo,
            'no_certificado': ('%x' % int(certificate_sudo.serial_number))[1::2],
            'certificado': certificate_sudo._get_der_certificate_bytes(formatting='base64').decode(),
            'emisor': {
                'supplier': supplier,
                'rfc': supplier.vat,
                'nombre': self._cfdi_sanitize_to_legal_name(root_company.name),
                'regimen_fiscal': fiscal_regime,
                'domicilio_fiscal_receptor': supplier.zip,
            },
        })

    @api.model
    def _add_currency_cfdi_values(self, cfdi_values, currency):
        """ Add the values about the currency to 'cfdi_values'.

        :param cfdi_values: The current CFDI values.
        :param currency:    The currency to consider.
        """
        currency_precision = currency.l10n_mx_edi_decimal_places

        def format_float(amount, precision=currency_precision):
            if amount is None or amount is False:
                return None
            # Avoid things like -0.0, see: https://stackoverflow.com/a/11010869
            amount = float_round(amount, precision_digits=precision)
            return '%.*f' % (precision, amount if not float_is_zero(amount, precision_digits=precision) else 0.0)

        cfdi_values.update({
            'format_float': format_float,
            'currency': currency,
            'currency_precision': currency_precision,
            'moneda': currency.name,
        })

    @api.model
    def _add_document_name_cfdi_values(self, cfdi_values, document_name):
        """ Add the values about the name of the document to 'cfdi_values'.

        :param cfdi_values:     The current CFDI values.
        :param document_name:   The name of the document.
        """
        name_numbers = list(re.finditer(r'\d+', document_name))
        cfdi_values.update({
            'document_name': document_name,
            'folio': name_numbers[-1].group().lstrip('0'),
            'serie': document_name[:name_numbers[-1].start()],
        })

    @api.model
    def _add_document_origin_cfdi_values(self, cfdi_values, document_origin):
        """ Add the values about the origin of the document to 'cfdi_values'.

        :param cfdi_values:     The current CFDI values.
        :param document_origin: The origin of the document.
        """
        origin_type = None
        origin_uuids = []
        splitted = (document_origin or '').split('|')
        if len(splitted) == 2:
            try:
                code = int(splitted[0])
                if 1 <= code <= 7:
                    origin_type = splitted[0]
                    origin_uuids = [uuid.strip() for uuid in splitted[1].split(',') if uuid]
            except ValueError:
                pass

        cfdi_values['tipo_relacion'] = origin_type
        cfdi_values['cfdi_relationado_list'] = origin_uuids

    @api.model
    def _get_datetime_now_with_mx_timezone(self, cfdi_values, journal=None):
        issued_address = cfdi_values['issued_address']
        tz = issued_address._l10n_mx_edi_get_cfdi_timezone()
        if journal:
            tz_force = self.env['ir.config_parameter'].sudo().get_param(f'l10n_mx_edi_tz_{journal.id}', default=None)
            if tz_force:
                tz = timezone(tz_force)
        return datetime.now(tz)

    @api.model
    def _add_date_cfdi_values(self, cfdi_values, document_date, journal=None, document_post_time=None):
        """ Add the values about the date of the document to 'cfdi_values'.

        :param cfdi_values:        The current CFDI values.
        :param document_date:      The date of the document.
        :param journal:            An optional accounting journal to retrieve the custom timezone from it.
        :param document_post_time: An optional exact time of sending the document if available.
        """
        if document_post_time:
            cfdi_date = document_post_time
        else:
            cfdi_date = self._get_min_of_now_and_document_date(document_date, cfdi_values['issued_address'], journal=journal)

        cfdi_values['fecha'] = cfdi_date.strftime(CFDI_DATE_FORMAT)

    def _get_min_of_now_and_document_date(self, document_date, issued_address, journal=None):
        """ This method returns the lesser of the document date and the current time in the
        Mexican timezone determined by the issued address and the journal. """
        cfdi_values = {'issued_address': issued_address}
        now_mx = self._get_datetime_now_with_mx_timezone(cfdi_values, journal).replace(tzinfo=None)
        document_datetime = datetime.combine(document_date, time(hour=23, minute=59, second=00))
        min_datetime = min(document_datetime, now_mx)
        return min_datetime

    @api.model
    def _add_payment_policy_cfdi_values(self, cfdi_values, payment_policy=None, payment_method=None):
        """ Add the values about the payment way of the document to 'cfdi_values'.

        :param cfdi_values:         The current CFDI values.
        :param payment_policy:      PPD or PUE.
        :param payment_method:      In case of PUE, a payment method is necessary.
        """
        if payment_policy == 'PPD':
            cfdi_values['metodo_pago'] = 'PPD'
            cfdi_values['forma_pago'] = '99'
        else:
            cfdi_values['metodo_pago'] = 'PUE'
            cfdi_values['forma_pago'] = (payment_method.code or '').replace('NA', '99')

    @api.model
    def _add_customer_cfdi_values(self, cfdi_values, customer=None, usage=None, to_public=False):
        """ Add the values about the customer to 'cfdi_values'.

        :param cfdi_values:     The current CFDI values.
        :param customer:        The partner if not PUBLICO EN GENERAL.
        :param usage:           The partner's reason to ask for this CFDI.
        :param to_public:       'CFDI to public' mode.
        """
        customer = customer or self.env['res.partner']
        invoice_customer = customer if customer.type == 'invoice' else customer.commercial_partner_id
        has_missing_vat = not invoice_customer.vat
        issued_address = cfdi_values['issued_address']

        # If the CFDI is refunding a global invoice, it should be sent as a refund of a global invoice with
        # ad 'publico en general'.
        is_refund_gi = False
        if cfdi_values.get('tipo_de_comprobante') == 'E' and cfdi_values.get('tipo_relacion') in ('01', '03'):
            # Force uso_cfdi to G02 since it's a refund of a global invoice.
            origin_uuids = cfdi_values['cfdi_relationado_list']
            is_refund_gi = bool(self.search([('attachment_uuid', 'in', origin_uuids), ('state', '=', 'ginvoice_sent')], limit=1))

        customer_as_publico_en_general = (not customer and to_public) or is_refund_gi
        customer_as_xexx_xaxx = to_public or customer.country_id.code != 'MX' or has_missing_vat

        if customer_as_publico_en_general or customer_as_xexx_xaxx:
            customer_values = {
                'to_public': True,
                'residencia_fiscal': None,
                'domicilio_fiscal_receptor': issued_address.zip,
                'regimen_fiscal_receptor': '616',
            }

            # Default UsoCFDI is S01 (no tax effects).
            uso_cfdi = 'S01'
            # Exception: credit notes (E) may use G02 under regime 616 or foreign regime.
            if cfdi_values.get('tipo_de_comprobante') == 'E' and (usage == 'G02' or is_refund_gi):
                uso_cfdi = 'G02'

            if customer_as_publico_en_general:
                customer_values.update({
                    'rfc': 'XAXX010101000',
                    'nombre': "PUBLICO EN GENERAL",
                    'uso_cfdi': uso_cfdi,
                })
            else:
                has_country = bool(customer.country_id)
                company = cfdi_values['company']
                export_fiscal_position = company._l10n_mx_edi_get_foreign_customer_fiscal_position()
                fiscal_position = customer.with_company(company).property_account_position_id
                has_export_fiscal_position = export_fiscal_position and fiscal_position == export_fiscal_position
                is_foreign_customer = customer.country_id.code != 'MX' and (has_country or has_export_fiscal_position)

                customer_values.update({
                    'rfc': 'XEXX010101000' if is_foreign_customer else 'XAXX010101000',
                    'nombre': self._cfdi_sanitize_to_legal_name(invoice_customer.commercial_company_name or invoice_customer.name),
                    'uso_cfdi': uso_cfdi,
                })
        else:
            customer_values = {
                'to_public': False,
                'rfc': invoice_customer.vat.strip(),
                'nombre': self._cfdi_sanitize_to_legal_name(invoice_customer.commercial_company_name or invoice_customer.name),
                'domicilio_fiscal_receptor': invoice_customer.zip,
                'regimen_fiscal_receptor': invoice_customer.l10n_mx_edi_fiscal_regime or '616',
                'uso_cfdi': usage if usage != 'P01' else 'S01',
            }
            if invoice_customer.country_id.l10n_mx_edi_code == 'MEX':
                customer_values['residencia_fiscal'] = None
            else:
                customer_values['residencia_fiscal'] = invoice_customer.country_id.l10n_mx_edi_code

        customer_values['customer'] = invoice_customer
        customer_values['issued_address'] = issued_address
        cfdi_values.update({
            'receptor': customer_values,
            'lugar_expedicion': issued_address.zip,
        })

    @api.model
    def _add_tax_objected_cfdi_values(self, cfdi_values, base_lines):
        """ Add the values about the tax objective of the document to 'cfdi_values'.

        :param cfdi_values:     The current CFDI values.
        :param base_lines:      A list of dictionaries representing the lines of the document.
        """
        customer = cfdi_values['receptor']['customer']
        if customer.l10n_mx_edi_no_tax_breakdown:
            # Tax exempted.
            tax_objected = '03'
        elif all(not x['tax_ids'] for x in base_lines):
            tax_objected = '01'
        else:
            tax_objected = '02'
        cfdi_values['objeto_imp'] = tax_objected

    @api.model
    def _add_and_round_tax_details(self, base_lines, company, tax_lines=None):
        """ Add the tax details on the base lines and round them.

        :param base_lines:          A list of base lines generated using the '_prepare_base_line_for_taxes_computation' method.
        :param company:             The company owning the base lines.
        :param tax_lines:           A optional list of base lines generated using the '_prepare_tax_line_for_taxes_computation'
                                    method. If specified, the tax amounts will be computed based on those existing tax lines.
                                    It's used to keep the manual tax amounts set by the user.
        :return:                    A new list of base lines.
        """
        AccountTax = self.env['account.tax']

        AccountTax._add_tax_details_in_base_lines(base_lines, company)
        AccountTax._round_base_lines_tax_details(base_lines, company, tax_lines=tax_lines)

        for base_line in base_lines:
            is_negative = base_line['tax_details']['raw_total_excluded_currency'] < 0.0
            if is_negative and not base_line['special_type']:
                base_line['special_type'] = 'global_discount'
        return base_lines

    @api.model
    def _dispatch_negative_base_lines(self, base_lines, company):
        """ Dispatch the negative lines and put them on the others like discounts.
        - Pre-compute in advance some data on taxes_data to be used later on the aggregators.

        :param base_lines:                  A list of base lines generated using the '_prepare_base_line_for_taxes_computation' method.
        :param company:                     The company owning the base lines.
        :return:                            A dictionary containing:
            * base_lines:                       The remaining positive base lines.
            * remaining_negative_base_lines:    The remaining negative base lines.
            * nullified_base_lines:             The base lines that are fully discounted at the end.
        """
        AccountTax = self.env['account.tax']

        # Return of merchandise.
        # The negative lines will try to reduce the 'quantity' instead of be added as a discount.
        base_lines = AccountTax._dispatch_return_of_merchandise_lines(base_lines, company)
        AccountTax._squash_return_of_merchandise_lines(base_lines, company)

        # Global discount.
        # Let's spread the global discount equally across the others lines instead of adding the full amount
        # on the biggest lines.
        base_lines = AccountTax._dispatch_global_discount_lines(base_lines, company)
        AccountTax._squash_global_discount_lines(base_lines, company)

        results = {
            'base_lines': [],
            'remaining_negative_base_lines': [],
            'nullified_base_lines': [],
        }
        for base_line in base_lines:
            compare_results = base_line['currency_id'].compare_amounts(
                base_line['tax_details']['raw_total_excluded_currency'],
                0,
            )
            is_nullified = bool(
                not base_line['quantity']
                or not base_line['price_unit']
            )
            if is_nullified:
                results['nullified_base_lines'].append(base_line)
            elif compare_results < 0.0:
                results['remaining_negative_base_lines'].append(base_line)
            else:
                results['base_lines'].append(base_line)

        return results

    @api.model
    def _dispatch_cfdi_base_lines(self, base_lines):
        """ Process the base lines passed as parameter and try to distribute the negative ones across the
        others since negative lines are not allowed in the CFDI.

        :param base_lines:              A list of dictionaries representing the base lines.
        :return: A dictionary containing:
            * cfdi_lines:               A list of dictionaries representing the remaining base lines for the CFDI
                                        after the distribution of the negative lines.
            * orphan_negative_lines:    A list of remaining negative lines that failed to be distributed.
        """
        def same_document_first(candidate, negative_line):
            return negative_line.get('document_id') != candidate.get('document_id')

        def prior_records_first(candidate, negative_line):
            return candidate.get('record_id') not in negative_line.get('prior_record_ids', [])

        sorting_criteria = [same_document_first, prior_records_first] + self.env['account.tax']._get_negative_lines_sorting_candidate_criteria()
        return self.env['account.tax']._dispatch_negative_lines(base_lines, sorting_criteria=sorting_criteria)

    @api.model
    def _add_base_lines_tax_amounts(self, base_lines, company):
        AccountTax = self.env['account.tax']
        AccountTax._add_tax_details_in_base_lines(base_lines, company)

        for base_line in base_lines:
            discount = base_line['discount']
            price_unit = base_line['price_unit']
            quantity = base_line['quantity']
            tax_details = base_line['tax_details']
            price_subtotal = base_line['price_subtotal'] = tax_details['raw_total_excluded_currency']

            if discount == 100.0:
                gross_price_subtotal_before_discount = price_unit * quantity
            else:
                gross_price_subtotal_before_discount = price_subtotal / (1 - discount / 100.0)

            base_line['gross_price_subtotal'] = gross_price_subtotal_before_discount
            base_line['discount_amount_before_dispatching'] = gross_price_subtotal_before_discount - price_subtotal

            for tax_data in tax_details['taxes_data']:
                tax = tax_data['tax']
                l10n_mx_tax_data_values = tax_data['l10n_mx'] = {
                    'tipo_factor': tax.l10n_mx_factor_type,
                    'impuesto': TAX_TYPE_TO_CFDI_CODE.get(tax.l10n_mx_tax_type),
                    'is_withholding': tax.amount < 0.0,
                    'is_fixed': tax.amount_type in ('fixed', 'code'),
                }

                if l10n_mx_tax_data_values['tipo_factor'] == 'Cuota':
                    if tax.amount_type == 'fixed':
                        # The user is managing IEPS with fixed tax like 4.6555 * quantity.
                        # In that case, the tax amount will be the quota and the quantity will be the base.
                        l10n_mx_tax_data_values['tasa_o_cuota'] = tax.amount
                        l10n_mx_tax_data_values['scale_from_quantity'] = True
                        l10n_mx_tax_data_values['product_field'] = None
                    elif tax.amount_type == 'code':
                        # The user is managing IEPS with custom tax like 4.6555 * product.l10n_mx_quantity_in_ml.
                        # In that case, the tax amount will be retrieved from the formula as an arbitrary value, here 4.6555.
                        # The base amount will be retrieved from the product using the 'l10n_mx_quantity_in_ml' field.
                        pattern = r'-?(?:\d*\.\d+|\d+)'
                        candidates_amounts = re.findall(pattern, tax.formula)
                        l10n_mx_tax_data_values['tasa_o_cuota'] = abs(float(candidates_amounts[0])) if candidates_amounts else 0.0
                        pattern = r'\bquantity\b'
                        l10n_mx_tax_data_values['scale_from_quantity'] = bool(re.findall(pattern, tax.formula))
                        product_fields = tax.formula_decoded_info['product_fields']
                        l10n_mx_tax_data_values['product_field'] = product_fields[0] if product_fields else None
                    else:
                        # Wrong config.
                        l10n_mx_tax_data_values['tasa_o_cuota'] = 0.0
                        l10n_mx_tax_data_values['scale_from_quantity'] = False
                        l10n_mx_tax_data_values['product_field'] = None
                elif l10n_mx_tax_data_values['tipo_factor'] == 'Tasa':
                    l10n_mx_tax_data_values['tasa_o_cuota'] = abs(tax.amount / 100.0)
                else:
                    l10n_mx_tax_data_values['tasa_o_cuota'] = None

    @api.model
    def _dispatch_base_lines_tax_breakdown_taxes(self, cfdi_values, base_lines):
        """ Manage the tax breakdown. When set, all taxes except the local ones are merge into
        the base and disappear from the CFDI.

        :param cfdi_values:     The current CFDI values.
        :param base_lines:      A list of dictionaries representing the lines of the document.
        """
        tax_objected = cfdi_values['objeto_imp']

        for base_line in base_lines:
            tax_details = base_line['tax_details']
            taxes_data = tax_details['taxes_data']

            if base_line['discount'] != 100.0 and any(tax_data['tax'].l10n_mx_tax_type != 'local' for tax_data in taxes_data):
                base_line['tax_objected'] = tax_objected
            else:
                base_line['tax_objected'] = '01'

            # Exclude some 'tax_data' in case of tax breakdown.
            new_taxes_data = tax_details['taxes_data'] = []
            for tax_data in taxes_data:
                tax = tax_data['tax']
                if (
                    # Local taxes are not affected.
                    tax.l10n_mx_tax_type != 'local'
                    and (
                        # No tax breakdown:
                        base_line['tax_objected'] in ('01', '03', '04', '05')
                    )
                ):
                    tax_details['raw_total_excluded_currency'] += tax_data['raw_tax_amount_currency']
                    tax_details['raw_total_excluded'] += tax_data['raw_tax_amount']
                    tax_details['total_excluded_currency'] += tax_data['tax_amount_currency']
                    tax_details['total_excluded'] += tax_data['tax_amount']
                else:
                    new_taxes_data.append(tax_data)

    @api.model
    def _add_base_lines_cfdi_values(self, cfdi_values, base_lines, global_invoice=False):
        """ Add the values about the lines to 'cfdi_values'.

        :param cfdi_values:     The current CFDI values.
        :param base_lines:      A list of dictionaries representing the lines of the document.
        :param global_invoice:  Indicate if the document is a global invoice.
        """
        AccountTax = self.env['account.tax']
        currency = cfdi_values['currency']
        company = cfdi_values['company']
        is_refund_gi = cfdi_values['receptor']['uso_cfdi'] == 'G02'
        cfdi_values['base_lines'] = base_lines

        # Manage tax breakdown.
        self._dispatch_base_lines_tax_breakdown_taxes(cfdi_values, base_lines)

        # Add 'raw_gross_total_excluded_currency' (a.k.a. 'importe') / 'raw_discount_amount_currency' (a.k.a. 'descuento').
        # Round all the values with 6 digits and ensure ROUND(SUM(...)) gives exactly the expected total of the document.
        AccountTax._round_raw_total_excluded(
            base_lines=base_lines,
            company=cfdi_values['company'],
            precision_digits=6,
            apply_strict_tolerance=True,
        )
        AccountTax._add_and_round_raw_gross_total_excluded_and_discount(
            base_lines=base_lines,
            company=cfdi_values['company'],
            precision_digits=6,
            account_discount_base_lines=True,
            apply_strict_tolerance=True,
        )

        # Pre-compute some values in base_line under 'l10n_mx_cfdi_values' and a grouping key per tax_data under 'l10n_mx_tax_grouping_key'.
        for base_line in base_lines:
            tax_details = base_line['tax_details']
            product = base_line['product_id']
            quantity = base_line['quantity']

            base_line_cfdi_values = base_line['l10n_mx_cfdi_values'] = {
                'cantidad': quantity,
                'descuento': tax_details['raw_discount_amount_currency'],
                'importe': tax_details['raw_gross_total_excluded_currency'],
                'traslados_list': [],
                'retenciones_list': [],
                'objeto_imp': base_line['tax_objected'],
            }

            if base_line_cfdi_values['cantidad']:
                base_line_cfdi_values['valor_unitario'] = base_line_cfdi_values['importe'] / base_line_cfdi_values['cantidad']
            else:
                base_line_cfdi_values['valor_unitario'] = 0.0

            if global_invoice:
                base_line_cfdi_values['clave_prod_serv'] = '01010101'
                base_line_cfdi_values['clave_unidad'] = 'ACT'
                base_line_cfdi_values['description'] = "Venta"
                base_line_cfdi_values['no_identificacion'] = base_line['_document_name']
                base_line_cfdi_values['cuenta_predial'] = None
                base_line_cfdi_values['unidad'] = None
            elif is_refund_gi:
                base_line_cfdi_values['clave_prod_serv'] = '84111506'
                base_line_cfdi_values['clave_unidad'] = 'ACT'
                base_line_cfdi_values['description'] = base_line['name']
                base_line_cfdi_values['no_identificacion'] = product.default_code
                base_line_cfdi_values['cuenta_predial'] = product.l10n_mx_edi_predial_account
                base_line_cfdi_values['unidad'] = (base_line['uom_id'].name or '').upper()
            else:
                base_line_cfdi_values['clave_prod_serv'] = base_line.get('product_unspsc_code') or product.unspsc_code_id.code
                base_line_cfdi_values['clave_unidad'] = base_line.get('uom_unspsc_code') or base_line['uom_id'].unspsc_code_id.code
                base_line_cfdi_values['description'] = base_line['name']
                base_line_cfdi_values['no_identificacion'] = product.default_code
                base_line_cfdi_values['cuenta_predial'] = product.l10n_mx_edi_predial_account
                base_line_cfdi_values['unidad'] = (base_line['uom_id'].name or '').upper()

            for tax_data in tax_details['taxes_data']:
                tax = tax_data['tax']
                local_tax_name = tax.tax_group_id.name if tax.l10n_mx_tax_type == 'local' else None
                tax_grouping_key = tax_data['l10n_mx_tax_grouping_key'] = {
                    'tipo_factor': tax.l10n_mx_factor_type,
                    'impuesto': TAX_TYPE_TO_CFDI_CODE.get(tax.l10n_mx_tax_type),
                    'is_withholding': tax.amount < 0.0,
                    'local_tax_name': local_tax_name,
                }

                if tax_grouping_key['tipo_factor'] == 'Cuota':
                    if tax.amount_type == 'fixed':
                        # The user is managing IEPS with fixed tax like 4.6555 * quantity.
                        # In that case, the tax amount will be the quota and the quantity will be the base.
                        tax_grouping_key['tasa_o_cuota'] = tax.amount
                        tax_grouping_key['scale_from_quantity'] = True
                        tax_grouping_key['product_field'] = None
                    elif tax.amount_type == 'code':
                        # The user is managing IEPS with custom tax like 4.6555 * product.l10n_mx_quantity_in_ml.
                        # In that case, the tax amount will be retrieved from the formula as an arbitrary value, here 4.6555.
                        # The base amount will be retrieved from the product using the 'l10n_mx_quantity_in_ml' field.
                        pattern = r'-?(?:\d*\.\d+|\d+)'
                        candidates_amounts = re.findall(pattern, tax.formula)
                        tax_grouping_key['tasa_o_cuota'] = abs(float(candidates_amounts[0])) if candidates_amounts else 0.0
                        pattern = r'\bquantity\b'
                        tax_grouping_key['scale_from_quantity'] = bool(re.findall(pattern, tax.formula))
                        product_fields = tax.formula_decoded_info['product_fields']
                        tax_grouping_key['product_field'] = product_fields[0] if product_fields else None
                    else:
                        # Wrong config.
                        tax_grouping_key['tasa_o_cuota'] = 0.0
                        tax_grouping_key['scale_from_quantity'] = False
                        tax_grouping_key['product_field'] = None
                elif tax_grouping_key['tipo_factor'] == 'Tasa':
                    tax_grouping_key['tasa_o_cuota'] = abs(tax.amount / 100.0)
                else:
                    tax_grouping_key['tasa_o_cuota'] = None

                if local_tax_name:
                    if tax.amount_type in ('fixed', 'code'):
                        tax_grouping_key['tasade'] = tax_grouping_key['tasa_o_cuota']
                    else:
                        tax_grouping_key['tasade'] = tax_grouping_key['tasa_o_cuota'] * 100.0
                else:
                    tax_grouping_key['tasade'] = None

        # Populate 'traslados_list' / 'retenciones_list' for each base_line.
        def regular_tax_grouping_function(base_line, tax_data):
            return (
                tax_data['l10n_mx_tax_grouping_key']
                if tax_data
                and not tax_data['l10n_mx_tax_grouping_key']['local_tax_name']
                else None
            )

        base_lines_aggregated_values = AccountTax._aggregate_base_lines_tax_details(base_lines, regular_tax_grouping_function)
        AccountTax._round_raw_tax_amounts(
            base_lines_aggregated_values=base_lines_aggregated_values,
            company=company,
            precision_digits=6,
            apply_strict_tolerance=True,
        )
        for base_line, aggregated_values in base_lines_aggregated_values:
            for grouping_key, values in aggregated_values.items():
                if not grouping_key:
                    continue

                is_withholding = grouping_key['is_withholding']
                tax_values = {
                    'impuesto': grouping_key['impuesto'],
                    'tipo_factor': grouping_key['tipo_factor'],
                    'tasa_o_cuota': grouping_key['tasa_o_cuota'],
                    'importe': float_round(values['raw_tax_amount_currency'] * (-1 if is_withholding else 1), precision_digits=6),
                }

                if grouping_key['tipo_factor'] == 'Cuota':
                    if grouping_key['scale_from_quantity']:
                        tax_values['base'] = float_round(base_line['quantity'], precision_digits=6)
                    elif grouping_key['product_field']:
                        tax_values['base'] = float_round(base_line['product_id'][grouping_key['product_field']], precision_digits=6)
                    else:
                        tax_values['base'] = 0.0
                else:
                    tax_values['base'] = float_round(values['raw_base_amount_currency'], precision_digits=6)
                    if float_is_zero(tax_values['base'], precision_digits=6):
                        tax_values['base'] = 0.000001

                target_list = 'retenciones_list' if is_withholding else 'traslados_list'
                base_line['l10n_mx_cfdi_values'][target_list].append(tax_values)

        # Populate 'traslados_list' / 'retenciones_list' for the whole document.
        cfdi_values['retenciones_list'] = []
        cfdi_values['retenciones_reduced_list'] = []
        cfdi_values['traslados_list'] = []

        values_per_grouping_key = AccountTax._aggregate_base_lines_aggregated_values(base_lines_aggregated_values)
        for grouping_key, values in values_per_grouping_key.items():
            if not grouping_key:
                continue

            is_withholding = grouping_key['is_withholding']

            tax_values = {
                'impuesto': grouping_key['impuesto'],
                'tipo_factor': grouping_key['tipo_factor'],
                'tasa_o_cuota': grouping_key['tasa_o_cuota'],
                'importe': values['tax_amount_currency'] * (-1 if is_withholding else 1),
            }
            if grouping_key['tipo_factor'] == 'Cuota':
                if grouping_key['scale_from_quantity']:
                    tax_values['base'] = sum(
                        float_round(base_line['quantity'], precision_digits=6)
                        for base_line, _taxes_data in values['base_line_x_taxes_data']
                    )
                elif grouping_key['product_field']:
                    tax_values['base'] = sum(
                        float_round(base_line['product_id'][grouping_key['product_field']], precision_digits=6)
                        for base_line, _taxes_data in values['base_line_x_taxes_data']
                        if base_line['product_id']
                    )
                else:
                    tax_values['base'] = 0.0
            else:
                tax_values['base'] = values['raw_base_amount_currency']

            target_list = 'retenciones_list' if is_withholding else 'traslados_list'
            cfdi_values[target_list].append(tax_values)

            if is_withholding:
                cfdi_values['retenciones_reduced_list'].append(dict(tax_values))

        # Populate 'local_traslados_list' / 'local_retenciones_list' for the whole document.
        cfdi_values['local_retenciones_list'] = []
        cfdi_values['local_traslados_list'] = []

        def local_tax_grouping_function(base_line, tax_data):
            grouping_key = (
                tax_data['l10n_mx_tax_grouping_key']
                if tax_data
                and tax_data['l10n_mx_tax_grouping_key']['local_tax_name']
                else None
            )
            if grouping_key is not None:
                if tax_data['tax'].amount_type in ('fixed', 'code'):
                    grouping_key['tasade'] = grouping_key['tasa_o_cuota']
                else:
                    grouping_key['tasade'] = grouping_key['tasa_o_cuota'] * 100.0

            return grouping_key

        base_lines_aggregated_values = AccountTax._aggregate_base_lines_tax_details(base_lines, local_tax_grouping_function)
        values_per_grouping_key = AccountTax._aggregate_base_lines_aggregated_values(base_lines_aggregated_values)
        for grouping_key, values in values_per_grouping_key.items():
            if not grouping_key:
                continue

            is_withholding = grouping_key['is_withholding']
            target_list = 'local_retenciones_list' if grouping_key['is_withholding'] else 'local_traslados_list'
            cfdi_values[target_list].append({
                'local_tax_name': grouping_key['local_tax_name'],
                'tasade': grouping_key['tasade'],
                'impuesto': grouping_key['impuesto'],
                'tipo_factor': grouping_key['tipo_factor'],
                'tasa_o_cuota': grouping_key['tasa_o_cuota'],
                'importe': values['tax_amount_currency'] * (-1 if is_withholding else 1),
                'base': values['base_amount_currency'],
            })

        # Add 'conceptos_list'.
        cfdi_values['conceptos_list'] = [
            base_line['l10n_mx_cfdi_values']
            for base_line in base_lines
        ]
        # Document's 'descuento'.
        cfdi_values['descuento'] = currency.round(sum(concepto['descuento'] for concepto in cfdi_values['conceptos_list']))
        cfdi_values['subtotal'] = cfdi_values['descuento']

        # Document's 'subtotal' / 'total'.
        def grouping_function(base_line, tax_data):
            return True

        base_lines_aggregated_values = AccountTax._aggregate_base_lines_tax_details(base_lines, grouping_function)
        values_per_grouping_key = AccountTax._aggregate_base_lines_aggregated_values(base_lines_aggregated_values)
        cfdi_values['total'] = 0.0
        for values in values_per_grouping_key.values():
            cfdi_values['subtotal'] += values['total_excluded_currency']
            cfdi_values['total'] += values['total_excluded_currency'] + values['tax_amount_currency']

        # Document's tax totals.
        for target_key, list_key in (
            ('total_impuestos_trasladados', 'traslados_list'),
            ('total_local_impuestos_trasladados', 'local_traslados_list'),
            ('total_impuestos_retenidos', 'retenciones_list'),
            ('total_local_impuestos_retenidos', 'local_retenciones_list'),
        ):
            tax_amounts = [
                x['importe']
                for x in cfdi_values[list_key]
                if x.get('tipo_factor') != 'Exento'
            ]
            cfdi_values[target_key] = sum(tax_amounts)
            cfdi_values[f'need_{target_key}'] = bool(tax_amounts)

        # Cleanup attributes for Exento taxes/descuento.
        if currency.is_zero(cfdi_values['descuento']):
            cfdi_values['descuento'] = None
        for concepto in cfdi_values['conceptos_list']:
            if currency.is_zero(concepto['descuento']):
                concepto['descuento'] = None
            for key in ('traslados_list', 'retenciones_list'):
                for tax_values in concepto[key]:
                    if tax_values['tipo_factor'] == 'Exento':
                        tax_values['importe'] = None
        for key in ('retenciones_list', 'traslados_list', 'local_retenciones_list', 'local_traslados_list'):
            for tax_values in cfdi_values[key]:
                if tax_values.get('tipo_factor') == 'Exento':
                    tax_values['importe'] = None
        if not cfdi_values['need_total_impuestos_trasladados']:
            cfdi_values['total_impuestos_trasladados'] = None
        if not cfdi_values['need_total_impuestos_retenidos']:
            cfdi_values['total_impuestos_retenidos'] = None

    @api.model
    def _get_post_fix_tax_amounts_map(self, base_amount, tax_amount, tax_rate, precision_digits):
        if float_round(abs(base_amount * tax_rate - tax_amount), precision_digits, rounding_method='DOWN') == 0.0:
            new_base_amount = float_round(base_amount, precision_digits=precision_digits)
            new_tax_amount = float_round(tax_amount, precision_digits=precision_digits)
        else:
            total = base_amount + tax_amount
            new_base_amount = float_round(total / (1 + tax_rate), precision_digits=precision_digits)
            new_tax_amount = total - new_base_amount
        return {
            'new_base_amount': new_base_amount,
            'new_tax_amount': new_tax_amount,
            'delta_base_amount': new_base_amount - base_amount,
            'delta_tax_amount': new_tax_amount - tax_amount,
        }

    @api.model
    def _clean_cfdi_values(self, cfdi_values):
        """ Clean values from 'cfdi_values' that could represent a security risk like sudoed records.

        :param cfdi_values: The current CFDI values.
        """
        def clean_node(values):
            to_clear = []
            for k, v in values.items():
                if isinstance(v, dict):
                    clean_node(v)
                elif isinstance(v, (list, tuple)):
                    for v2 in v:
                        if isinstance(v2, dict):
                            clean_node(v2)
                elif isinstance(v, models.Model):
                    if v.env.su:
                        to_clear.append(k)
            for k in to_clear:
                values.pop(k)

        clean_node(cfdi_values)

    @api.model
    def _convert_xml_to_attachment_data(self, xml_string):
        """
        Create and return a raw XML string value with custom hardcoded declaration.
        This ensures the generated string to have double quote in the XML declaration,
        because some third party vendors do not accept single quoted declaration.
        """
        custom_declaration = b'<?xml version="1.0" encoding="UTF-8"?>\n'
        return custom_declaration + etree.tostring(
            element_or_tree=xml_string,
            pretty_print=True,
            encoding='UTF-8',
        )

    # -------------------------------------------------------------------------
    # GLOBAL CFDI
    # -------------------------------------------------------------------------

    @api.model
    def _get_global_invoice_cfdi_sequence(self, company, create_if_missing=True):
        """ Get or create the ir.sequence to be used to get the global invoice document name.

        :param company:             The company owning the sequence.
        :param create_if_missing:   Create the sequence if not exists yet.
        :return:                    An ir.sequence record.
        """
        sequence = company.l10n_mx_edi_global_invoice_sequence_id
        if sequence:
            return sequence
        if not sequence and create_if_missing:
            return company._create_l10n_mx_edi_global_invoice_sequence()

    @api.model
    def _consume_global_invoice_cfdi_sequence(self, sequence, number_next):
        """ Update the ir.sequence used to get the folio of the global invoice.

        :param sequence:        The sequence.
        :param number_next:     The consumed number.
        :return:
        """
        sudo_sequence = sequence.sudo()
        sudo_sequence.number_next = number_next + 1
        sudo_sequence.flush_recordset(fnames=['number_next'])

    @api.model
    def _add_global_invoice_cfdi_values(self, cfdi_values, cfdi_lines, document_date=None, periodicity='04', origin=None):
        """ Add the generic values about the global invoice in 'cfdi_values'.

        :param cfdi_values:     The cfdi_values collected so far.
        :param cfdi_lines:      The lines in the global invoice.
        :param document_date:   The date of the global invoice.
        :param periodicity:     The periodicity. Default is '04'. See 'GLOBAL_INVOICE_PERIODICITY_DEFAULT_VALUES'.
        :param origin:          The origin of the CFDI when creating a replacement.
        """
        AccountTax = self.env['account.tax']

        def add_or_none(results, tax_values, key):
            """ Little helper to add an amount by taking care of keeping the None value (for example for 'importe' value).
            For some taxes, we don't want to see this attribute (e.g. Exento). So the idea is to keep the original value
            as None until we found a tax having a not None 'importe' amount.

            :param results:     The results in which we need to add the 'importe' amount.
            :param tax_values:  A dictionary containing the 'importe' amount of the tax.
            :param key:         The key to access the results.
            """
            if tax_values[key] is not None:
                results[key] = results[key] or 0.0
                results[key] += tax_values[key]

        currency = cfdi_lines[0]['currency_id']
        rates = []
        if currency.name != 'MXN':
            parents = set()
            for line in cfdi_lines:
                if line['rate'] and line['document_name'] not in parents:
                    parents.add(line['document_name'])
                    rates.append(1 / line['rate'])
        rate = sum(rates) / len(rates) if rates else None

        self._add_base_cfdi_values(cfdi_values)
        self._add_currency_cfdi_values(cfdi_values, currency)
        self._add_document_origin_cfdi_values(cfdi_values, origin)
        self._add_customer_cfdi_values(cfdi_values, to_public=True)

        # Group lines per document_name / tax_ids.
        def grouping_function(base_line, tax_data):
            return {
                'tax_ids': base_line['tax_ids'],
                '_document_name': base_line['document_name'],
            }

        new_base_lines = []
        base_lines_aggregated_values = AccountTax._aggregate_base_lines_tax_details(cfdi_lines, grouping_function)
        values_per_grouping_key = AccountTax._aggregate_base_lines_aggregated_values(base_lines_aggregated_values)
        for grouping_key, values in values_per_grouping_key.items():
            aggregated_base_lines = [
                base_line
                for base_line, _taxes_data in values['base_line_x_taxes_data']
            ]
            aggregated_tax_details = None
            for base_line in aggregated_base_lines:
                if aggregated_tax_details:
                    aggregated_tax_details = AccountTax._merge_tax_details(
                        tax_details_1=aggregated_tax_details,
                        tax_details_2=base_line['tax_details'],
                    )
                else:
                    aggregated_tax_details = base_line['tax_details']
            new_base_line = AccountTax._prepare_base_line_for_taxes_computation(
                None,
                tax_ids=grouping_key['tax_ids'],
                price_unit=sum(
                    base_line['price_unit'] * (1 - (base_line['discount'] / 100.0)) * base_line['quantity']
                    for base_line in aggregated_base_lines
                ),
                discount_amount=0.0,
                quantity=1.0,
                currency_id=currency,
                rate=rate or 1.0,
                tax_details=aggregated_tax_details,
                _document_name=grouping_key['_document_name'],
            )
            new_base_lines.append(new_base_line)

        self._add_tax_objected_cfdi_values(cfdi_values, new_base_lines)
        self._add_base_lines_cfdi_values(cfdi_values, new_base_lines, True)

        # Sequence:
        sequence = self._get_global_invoice_cfdi_sequence(cfdi_values['company'], create_if_missing=False)
        if not sequence:
            sequence = self._get_global_invoice_cfdi_sequence(cfdi_values['root_company'])
        cfdi_date = fields.Date.context_today(self)
        str_date = fields.Date.to_string(cfdi_date)
        folio = str(sequence.number_next)
        serie, _interpolated_suffix = sequence._get_prefix_suffix(date=str_date, date_range=str_date)

        # Periodicity.
        document_date = document_date or cfdi_date
        month = document_date.month
        if periodicity == '05':
            periodicity_month = int(12 + ((month + (month % 2)) / 2))
        else:
            periodicity_month = month

        cfdi_values.update({
            'sequence': sequence,
            'folio': folio,
            'serie': serie,
            'fecha': cfdi_date.strftime(CFDI_DATE_FORMAT),
            'tipo_cambio': sum(rates) / len(rates) if rates else None,
            'information_global': {
                'periodicidad': periodicity,
                'meses': str(periodicity_month).rjust(2, '0'),
                'ano': str(document_date.year),
            },
            'condiciones_de_pago': None,
            'tipo_de_comprobante': 'I',
        })

    # -------------------------------------------------------------------------
    # CFDI: PACs
    # -------------------------------------------------------------------------

    @api.model
    def _get_finkok_credentials(self, company):
        ''' Return the company credentials for PAC: finkok. Does not depend on a recordset
        '''
        if company.l10n_mx_edi_pac_test_env:
            return {
                'username': 'cfdi@vauxoo.com',
                'password': 'vAux00__',
                'sign_url': 'http://demo-facturacion.finkok.com/servicios/soap/stamp.wsdl',
                'cancel_url': 'http://demo-facturacion.finkok.com/servicios/soap/cancel.wsdl',
            }
        else:
            if not company.sudo().l10n_mx_edi_pac_username or not company.sudo().l10n_mx_edi_pac_password:
                return {
                    'errors': [_("The username and/or password are missing.")]
                }

            return {
                'username': company.sudo().l10n_mx_edi_pac_username,
                'password': company.sudo().l10n_mx_edi_pac_password,
                'sign_url': 'http://facturacion.finkok.com/servicios/soap/stamp.wsdl',
                'cancel_url': 'http://facturacion.finkok.com/servicios/soap/cancel.wsdl',
            }

    @api.model
    def _finkok_sign(self, credentials, cfdi):
        ''' Send the CFDI XML document to Finkok for signature. Does not depend on a recordset
        '''
        def get_in_error(error, key):
            if key in error:
                return error[key]

        try:
            client = Client(credentials['sign_url'], timeout=20)
            response = client.service.stamp(cfdi, credentials['username'], credentials['password'])
            # pylint: disable=broad-except
        except Exception as e:
            return {
                'errors': [_("The Finkok service failed to sign with the following error: %s", str(e))],
            }

        if response.Incidencias and not response.xml:
            error = response.Incidencias.Incidencia[0]

            code = get_in_error(error, 'CodigoError')
            msg = get_in_error(error, 'MensajeIncidencia')
            extra = get_in_error(error, 'ExtraInfo')

            errors = []
            if code:
                errors.append(_("Code : %s", code))
            if msg:
                errors.append(_("Message : %s", msg))
            if extra:
                errors.append(_("Extra Info : %s", extra))
            return {'errors': errors}

        cfdi_signed = response.xml if 'xml' in response else None
        if cfdi_signed:
            cfdi_signed = cfdi_signed.encode('utf-8')

        return {
            'cfdi_str': cfdi_signed,
        }

    @api.model
    def _finkok_cancel(self, cfdi_values, credentials, uuid, cancel_reason, cancel_uuid=None):
        company = cfdi_values['root_company']
        certificate_sudo = cfdi_values['certificate'].sudo()
        cer_pem = base64.b64decode(certificate_sudo.pem_certificate)
        key_pem = base64.b64decode(certificate_sudo.private_key_id.pem_key)
        try:
            client = Client(credentials['cancel_url'], timeout=20)
            factory = client.type_factory('apps.services.soap.core.views')
            uuid_type = factory.UUID()
            uuid_type.UUID = uuid
            uuid_type.Motivo = cancel_reason
            if cancel_uuid:
                uuid_type.FolioSustitucion = cancel_uuid
            docs_list = factory.UUIDArray(uuid_type)
            response = client.service.cancel(
                docs_list,
                credentials['username'],
                credentials['password'],
                company.vat,
                cer_pem,
                key_pem,
            )
            # pylint: disable=broad-except
        except Exception as e:
            return {
                'errors': [_("The Finkok service failed to cancel with the following error: %s", str(e))],
            }

        code = None
        msg = None
        if 'Folios' in response and response.Folios:
            if 'EstatusUUID' in response.Folios.Folio[0]:
                response_code = response.Folios.Folio[0].EstatusUUID
                if response_code not in ('201', '202'):
                    code = response_code
                    msg = _("Cancelling got an error")
        elif 'CodEstatus' in response:
            code = response.CodEstatus
            msg = _("Cancelling got an error")
        else:
            msg = _('A delay of 2 hours has to be respected before to cancel')

        errors = []
        if code:
            errors.append(_("Code : %s", code))
        if msg:
            errors.append(_("Message : %s", msg))
        if errors:
            return {'errors': errors}

        return {}

    @api.model
    def _get_solfact_credentials(self, company):
        ''' Return the company credentials for PAC: solucion factible. Does not depend on a recordset
        '''
        if company.l10n_mx_edi_pac_test_env:
            return {
                'username': 'testing@solucionfactible.com',
                'password': 'timbrado.SF.16672',
                'url': 'https://testing.solucionfactible.com/ws/services/Timbrado?wsdl',
            }
        else:
            if not company.sudo().l10n_mx_edi_pac_username or not company.sudo().l10n_mx_edi_pac_password:
                return {
                    'errors': [_("The username and/or password are missing.")]
                }

            return {
                'username': company.sudo().l10n_mx_edi_pac_username,
                'password': company.sudo().l10n_mx_edi_pac_password,
                'url': 'https://solucionfactible.com/ws/services/Timbrado?wsdl',
            }

    @api.model
    def _solfact_sign(self, credentials, cfdi):
        ''' Send the CFDI XML document to Solucion Factible for signature. Does not depend on a recordset
        '''
        try:
            client = Client(credentials['url'], timeout=20)
            response = client.service.timbrar(credentials['username'], credentials['password'], cfdi, False)
            # pylint: disable=broad-except
        except Exception as e:
            return {
                'errors': [_("The Solucion Factible service failed to sign with the following error: %s", str(e))],
            }

        if response.status != 200:
            # ws-timbrado-timbrar - status 200 : CFDI correctamente validado y timbrado.
            return {
                'errors': [_("The Solucion Factible service failed to sign with the following error: %s", response.mensaje)],
            }

        if response.resultados:
            result = response.resultados[0]
        else:
            result = response

        cfdi_signed = result.cfdiTimbrado if 'cfdiTimbrado' in result else None
        if cfdi_signed:
            return {
                'cfdi_str': cfdi_signed,
            }

        msg = result.mensaje if 'mensaje' in result else None
        code = result.status if 'status' in result else None
        errors = []
        if code:
            errors.append(_("Code : %s", code))
        if msg:
            errors.append(_("Message : %s", msg))
        return {'errors': errors}

    @api.model
    def _solfact_cancel(self, cfdi_values, credentials, uuid, cancel_reason, cancel_uuid=None):
        certificate = cfdi_values['certificate']
        uuid_param = f"{uuid}|{cancel_reason}|"
        if cancel_uuid:
            uuid_param += cancel_uuid
        cer_pem = base64.b64decode(certificate.pem_certificate)
        key_pem = base64.b64decode(certificate.private_key_id.pem_key)
        key_password = certificate.private_key_id.password

        try:
            client = Client(credentials['url'], timeout=20)
            response = client.service.cancelar(
                credentials['username'], credentials['password'],
                uuid_param, cer_pem, key_pem, key_password
            )
            # pylint: disable=broad-except
        except Exception as e:
            return {
                'errors': [_("The Solucion Factible service failed to cancel with the following error: %s", str(e))],
            }

        if response.status not in (200, 201):
            # ws-timbrado-cancelar - status 200 : El proceso de cancelación se ha completado correctamente.
            # ws-timbrado-cancelar - status 201 : El folio se ha cancelado con éxito.
            return {
                'errors': [_("The Solucion Factible service failed to cancel with the following error: %s", response.mensaje)],
            }

        if response.resultados:
            response_code = response.resultados[0].statusUUID if 'statusUUID' in response.resultados[0] else None
        else:
            response_code = response.status if 'status' in response else None

        # no show code and response message if cancel was success
        msg = None
        code = None
        if response_code not in ('201', '202'):
            code = response_code
            if response.resultados:
                result = response.resultados[0]
            else:
                result = response
            if 'mensaje' in result:
                msg = result.mensaje

        errors = []
        if code:
            errors.append(_("Code : %s", code))
        if msg:
            errors.append(_("Message : %s", msg))
        if errors:
            return {'errors': errors}

        return {}

    @api.model
    def _document_get_sw_token(self, credentials):
        if credentials['password'] and not credentials['username']:
            # token is configured directly instead of user/password
            return {
                'token': credentials['password'].strip(),
            }

        try:
            headers = {
                'user': credentials['username'],
                'password': credentials['password'],
                'Cache-Control': "no-cache"
            }
            response = requests.post(credentials['login_url'], headers=headers, timeout=20)
            response.raise_for_status()
            response_json = response.json()
            return {
                'token': response_json['data']['token'],
            }
        except (requests.exceptions.RequestException, KeyError, TypeError) as req_e:
            return {
                'errors': [str(req_e)],
            }

    @api.model
    def _get_sw_credentials(self, company):
        '''Get the company credentials for PAC: SW. Does not depend on a recordset
        '''
        if not company.sudo().l10n_mx_edi_pac_username or not company.sudo().l10n_mx_edi_pac_password:
            return {
                'errors': [_("The username and/or password are missing.")]
            }

        credentials = {
            'username': company.sudo().l10n_mx_edi_pac_username,
            'password': company.sudo().l10n_mx_edi_pac_password,
        }

        if company.l10n_mx_edi_pac_test_env:
            credentials.update({
                'login_url': 'https://services.test.sw.com.mx/security/authenticate',
                'sign_url': 'https://services.test.sw.com.mx/cfdi33/stamp/v3/b64',
                'cancel_url': 'https://services.test.sw.com.mx/cfdi33/cancel/csd',
            })
        else:
            credentials.update({
                'login_url': 'https://services.sw.com.mx/security/authenticate',
                'sign_url': 'https://services.sw.com.mx/cfdi33/stamp/v3/b64',
                'cancel_url': 'https://services.sw.com.mx/cfdi33/cancel/csd',
            })

        # Retrieve a valid token.
        credentials.update(self._document_get_sw_token(credentials))

        return credentials

    @api.model
    def _document_sw_call(self, url, headers, payload=None):
        try:
            response = requests.post(
                url,
                data=payload,
                headers=headers,
                verify=True,
                timeout=(20, 120),
            )
        except requests.exceptions.RequestException as req_e:
            return {'status': 'error', 'message': str(req_e)}
        msg = ""
        try:
            response.raise_for_status()
        except requests.exceptions.HTTPError as res_e:
            msg = str(res_e)
        try:
            response_json = response.json()
        except JSONDecodeError:
            # If it is not possible get json then
            # use response exception message
            return {'status': 'error', 'message': msg}
        if (response_json['status'] == 'error' and
                response_json['message'].startswith('307')):
            # XML signed previously
            cfdi = base64.encodebytes(
                response_json['messageDetail'].encode('UTF-8'))
            cfdi = cfdi.decode('UTF-8')
            response_json['data'] = {'cfdi': cfdi}
            # We do not need an error message if XML signed was
            # retrieved then cleaning them
            response_json.update({
                'message': None,
                'messageDetail': None,
                'status': 'success',
            })
        return response_json

    @api.model
    def _sw_sign(self, credentials, cfdi):
        ''' calls the SW web service to send and sign the CFDI XML.
        Method does not depend on a recordset
        '''
        cfdi_b64 = base64.encodebytes(cfdi).decode('UTF-8')
        random_values = [random.choice(string.ascii_letters + string.digits) for n in range(30)]
        boundary = ''.join(random_values)
        payload = """--%(boundary)s
Content-Type: text/xml
Content-Transfer-Encoding: binary
Content-Disposition: form-data; name="xml"; filename="xml"

%(cfdi_b64)s
--%(boundary)s--
""" % {'boundary': boundary, 'cfdi_b64': cfdi_b64}
        payload = payload.replace('\n', '\r\n').encode('UTF-8')

        headers = {
            'Authorization': "bearer " + credentials['token'],
            'Content-Type': ('multipart/form-data; '
                             'boundary="%s"') % boundary,
        }

        response_json = self._document_sw_call(credentials['sign_url'], headers, payload=payload)

        try:
            cfdi_signed = response_json['data']['cfdi']
        except (KeyError, TypeError):
            cfdi_signed = None

        if cfdi_signed:
            return {
                'cfdi_str': base64.decodebytes(cfdi_signed.encode('UTF-8')),
            }
        else:
            code = response_json.get('message')
            msg = response_json.get('messageDetail')
            errors = []
            if code:
                errors.append(_("Code : %s", code))
            if msg:
                errors.append(_("Message : %s", msg))
            return {'errors': errors}

    @api.model
    def _sw_cancel(self, cfdi_values, credentials, uuid, cancel_reason, cancel_uuid=None):
        company = cfdi_values['root_company']
        certificate_sudo = cfdi_values['certificate'].sudo()
        headers = {
            'Authorization': "bearer " + credentials['token'],
            'Content-Type': "application/json"
        }
        payload_dict = {
            'rfc': company.vat,
            'b64Cer': certificate_sudo.pem_certificate.decode('UTF-8'),
            'b64Key': certificate_sudo.private_key_id.pem_key.decode('UTF-8'),
            'password': certificate_sudo.private_key_id.password,
            'uuid': uuid,
            'motivo': cancel_reason,
        }
        if cancel_uuid:
            payload_dict['folioSustitucion'] = cancel_uuid
        payload = json.dumps(payload_dict)

        response_json = self._document_sw_call(credentials['cancel_url'], headers, payload=payload.encode('UTF-8'))

        cancelled = response_json['status'] == 'success'
        if cancelled:
            data_codes = response_json.get('data', {}).get('uuid', {}).values()
            data_code = next(iter(data_codes)) if data_codes else ''
            code = '' if data_code in ('201', '202') else data_code
            msg = '' if data_code in ('201', '202') else _("Cancelling got an error")
        else:
            code = response_json.get('message')
            msg = response_json.get('messageDetail')
        errors = []
        if code:
            errors.append(_("Code : %s", code))
        if msg:
            errors.append(_("Message : %s", msg))
        if errors:
            return {'errors': errors}

        return {}

    # -------------------------------------------------------------------------
    # BUSINESS METHODS
    # -------------------------------------------------------------------------

    def _create_update_document(self, records, document_values, accept_method):
        """ Create/update a new document.

        :param records:             The records owning the document.
        :param document_values:     The values to create the document.
        :param accept_method:       A method taking document can be updated.
        :return                     The newly created or updated document.
        """
        def create_attachment(attachment_values):
            return self.env['ir.attachment'].with_user(SUPERUSER_ID).create({
                **attachment_values,
                'res_model': records._name,
                'res_id': records.id if len(records) == 1 else None,
                'type': 'binary',
                'mimetype': 'application/xml',
            })

        today = fields.Datetime.now()
        result_document = None

        # Prepare values for the attachment.
        if isinstance(document_values.get('attachment_id'), dict):
            attachment_values = document_values.pop('attachment_id')

            # Pretty-print the xml.
            xml_string = etree.fromstring(attachment_values['raw'])
            attachment_values['raw'] = self.env['l10n_mx_edi.document']._convert_xml_to_attachment_data(xml_string)
        else:
            attachment_values = None

        for existing_document in self.sorted():
            if accept_method(existing_document):
                if attachment_values:
                    if existing_document.attachment_id:
                        existing_document.attachment_id.update(attachment_values)
                    else:
                        document_values['attachment_id'] = create_attachment(attachment_values).id

                existing_document.write({
                    'message': None,
                    **document_values,
                    'datetime': today,
                })
                result_document = existing_document
                break

        if not result_document:
            if attachment_values:
                document_values['attachment_id'] = create_attachment(attachment_values).id

            result_document = self.create({
                **document_values,
                'datetime': today,
            })

            # During Global Invoice creation, this method is called from an empty recordset `records=self.env['l10n_mx_edi.document']`.
            # In that case we want the attachment res_id to be the newly created document.
            # sudo because attachment made by SUPERUSER requires group_system to modify
            result_attachment = result_document.attachment_id
            if result_attachment.res_model == result_document._name and not result_attachment.res_id:
                result_attachment.with_user(SUPERUSER_ID).res_id = result_document.id

        return result_document

    @api.model
    def _create_update_invoice_document_from_invoice(self, invoice, document_values):
        """ Create/update a new document for invoice.

        :param invoice:         An invoice.
        :param document_values: The values to create the document.
        """
        # Never remove a document that is already recorded in the SAT system.
        remaining_documents = invoice.l10n_mx_edi_invoice_document_ids\
            .filtered(lambda doc: (
                doc.sat_state not in ('valid', 'cancelled', 'skip')
                or (doc.sat_state == 'cancelled' and doc.state == 'invoice_cancel_requested')
            ))

        if document_values['state'] in ('invoice_sent', 'invoice_cancel', 'invoice_cancel_requested'):
            accept_method_state = f"{document_values['state']}_failed"
        else:
            accept_method_state = document_values['state']

        document = remaining_documents._create_update_document(
            invoice,
            document_values,
            lambda x: x.state == accept_method_state,
        )

        document_states_to_remove = {
            'invoice_sent_failed',
            'invoice_cancel_requested_failed',
            'invoice_cancel_failed',
            'ginvoice_sent_failed',
            'ginvoice_cancel_failed',
        }

        # In case we successfully cancel the invoice, we no longer need the previous cancellation requests.
        # So, let's remove them.
        if document.state == 'invoice_cancel':
            document_states_to_remove.add('invoice_cancel_requested')

        remaining_documents\
            .filtered(lambda x: x != document and x.state in document_states_to_remove) \
            .unlink()

        if document.state in ('invoice_sent', 'invoice_cancel', 'invoice_cancel_requested'):
            remaining_documents \
                .exists() \
                .filtered(lambda x: x != document and x.attachment_uuid == document.attachment_uuid) \
                .write({'sat_state': 'skip'})

        return document

    @api.model
    def _create_update_payment_document(self, payment, document_values):
        """ Create/update a new document for payment.

        :param payment:         A payment reconciled with some invoices.
        :param document_values: The values to create the document.
        """
        # Never remove a document that is already recorded in the SAT system.
        remaining_documents = payment.l10n_mx_edi_payment_document_ids\
            .filtered(lambda doc: doc.sat_state not in ('valid', 'cancelled', 'skip'))

        if document_values['state'] in ('payment_sent', 'payment_sent_pue', 'payment_cancel'):
            accept_method_state = f"{document_values['state']}_failed"
        else:
            accept_method_state = document_values['state']

        document = remaining_documents\
            .filtered(lambda x: x.state not in ('payment_sent', 'payment_cancel'))\
            ._create_update_document(
                payment,
                document_values,
                lambda x: x.state in (accept_method_state, 'payment_sent_pue'),
            )

        remaining_documents \
            .filtered(lambda x: x != document and x.state in {'payment_sent_failed', 'payment_cancel_failed'}) \
            .unlink()

        if document.state in ('payment_sent', 'payment_cancel'):
            remaining_documents \
                .exists() \
                .filtered(lambda x: x != document and x.attachment_uuid == document.attachment_uuid) \
                .write({'sat_state': 'skip'})

        return document

    @api.model
    def _create_update_global_invoice_document_from_invoices(self, invoices, document_values):
        """ Create/update a new document for global invoice.

        :param invoices:        The related invoices.
        :param document_values: The values to create the document.
        """
        # Never remove a document that is already recorded in the SAT system.
        remaining_documents = invoices[0].l10n_mx_edi_invoice_document_ids\
            .filtered(lambda doc: doc.sat_state not in ('valid', 'cancelled', 'skip'))

        if document_values['state'] in ('ginvoice_sent', 'ginvoice_cancel'):
            accept_method_state = f"{document_values['state']}_failed"
        else:
            accept_method_state = document_values['state']

        document = remaining_documents._create_update_document(
            self,
            document_values,
            lambda x: x.state == accept_method_state,
        )

        remaining_documents \
            .filtered(lambda x: x != document and x.state in {
                'invoice_sent_failed',
                'invoice_cancel_failed',
                'ginvoice_sent_failed',
                'ginvoice_cancel_failed',
            }) \
            .unlink()

        if document.state in ('ginvoice_sent', 'ginvoice_cancel'):
            remaining_documents \
                .exists() \
                .filtered(lambda x: x != document and x.attachment_uuid == document.attachment_uuid) \
                .write({'sat_state': 'skip'})

        return document

    @api.model
    def _get_cadena_xslts(self):
        return 'l10n_mx_edi/data/4.0/xslt/cadenaoriginal_TFD.xslt', 'l10n_mx_edi/data/4.0/xslt/cadenaoriginal.xslt'

    @api.model
    def _decode_cfdi_attachment(self, cfdi_data):
        """ Extract relevant data from the CFDI attachment.

        :param: cfdi_data:      The cfdi data as raw bytes.
        :return:                A python dictionary.
        """
        cadena_tfd, cadena = self._get_cadena_xslts()

        def get_cadena(cfdi_node, template):
            if cfdi_node is None:
                return None
            cadena_root = etree.parse(tools.file_open(template))
            return str(etree.XSLT(cadena_root)(cfdi_node))

        def get_node(node, xpath):
            nodes = node.xpath(xpath)
            return nodes[0] if nodes else None

        def get_value(node, key):
            if node is None:
                return None
            upper_key = key[0].upper() + key[1:]
            lower_key = key[0].lower() + key[1:]
            return node.get(upper_key) or node.get(lower_key)

        # Nothing to decode.
        if not cfdi_data:
            return {}

        try:
            cfdi_node = etree.fromstring(cfdi_data)
            emisor_node = get_node(cfdi_node, "//*[local-name()='Emisor']")
            receptor_node = get_node(cfdi_node, "//*[local-name()='Receptor']")
            info_global_node = get_node(cfdi_node, "//*[local-name()='InformacionGlobal']")
            origin_node = get_node(cfdi_node, "//*[local-name()='CfdiRelacionados']")
            origin_nodes = cfdi_node.xpath("//*[local-name()='CfdiRelacionado']")
        except etree.XMLSyntaxError:
            # Not an xml
            return {}
        except AttributeError:
            # Not a CFDI
            return {}

        tfd_node = get_node(cfdi_node, "//*[local-name()='TimbreFiscalDigital']")
        origin_type = get_value(origin_node, 'TipoRelacion')
        origin_uuids = [origin_uuid for node in origin_nodes if (origin_uuid := get_value(node, 'UUID'))]
        if origin_type and origin_uuids:
            origin_uuids_str = ','.join(origin_uuids)
            origin = f'{origin_type}|{origin_uuids_str}'
        else:
            origin = None

        return {
            'uuid': get_value(tfd_node, 'UUID'),
            'supplier_rfc': get_value(emisor_node, 'Rfc'),
            'customer_rfc': get_value(receptor_node, 'Rfc'),
            'amount_total': get_value(cfdi_node, 'Total'),
            'cfdi_node': cfdi_node,
            'usage': get_value(receptor_node, 'UsoCFDI'),
            'payment_method': get_value(cfdi_node, 'formaDePago') or get_value(cfdi_node, 'MetodoPago'),
            'bank_account': get_value(cfdi_node, 'NumCtaPago'),
            'sello': get_value(cfdi_node, 'sello') or 'No identificado',
            'sello_sat': get_value(tfd_node, 'SelloSAT') or 'No identificado',
            'cadena': get_cadena(tfd_node, cadena_tfd) or get_cadena(cfdi_node, cadena),
            'certificate_number': get_value(cfdi_node, 'NoCertificado'),
            'certificate_sat_number': get_value(tfd_node, 'NoCertificadoSAT'),
            'expedition': get_value(cfdi_node, 'LugarExpedicion'),
            'fiscal_regime': get_value(emisor_node, 'RegimenFiscal') or '',
            'emission_date_str': (get_value(cfdi_node, 'Fecha') or '').replace('T', ' '),
            'stamp_date': (get_value(tfd_node, 'FechaTimbrado') or '').replace('T', ' '),
            'periodicity': get_value(info_global_node, 'Periodicidad'),
            'origin': origin,
        }

    @api.model
    def _send_api(self, company, qweb_template, cfdi_filename, on_populate, on_failure, on_success):
        """ Common way to send a document.

        :param company:         The company.
        :param qweb_template:   The template name to render the cfdi.
        :param cfdi_filename:   The filename of the document.
        :param on_failure:      The method to call in case of failure.
        :param on_success:      The method to call in case of success.
        """
        # == Check the config ==
        cfdi_values = self.env['l10n_mx_edi.document']._get_company_cfdi_values(company)
        if cfdi_values.get('errors'):
            on_failure("\n".join(cfdi_values['errors']))
            if self._can_commit():
                self._cr.commit()
            return

        root_company = cfdi_values['root_company']

        self.env['l10n_mx_edi.document']._add_certificate_cfdi_values(cfdi_values)
        if cfdi_values.get('errors'):
            on_failure("\n".join(cfdi_values['errors']))
            if self._can_commit():
                self._cr.commit()
            return

        # == CFDI values ==
        populate_return = on_populate(cfdi_values)
        if cfdi_values.get('errors'):
            on_failure("\n".join(cfdi_values['errors']))
            if self._can_commit():
                self._cr.commit()
            return

        # == Generate the CFDI ==
        certificate_sudo = cfdi_values['certificate'].sudo()
        self._clean_cfdi_values(cfdi_values)
        cfdi = self.env['ir.qweb']._render(qweb_template, cfdi_values)

        if 'cfdi_cartaporte' in qweb_template:
            # Since we are inheriting version 3.0 of the Carta Porte template,
            # we need to update both the namespace prefix and its URI to version 3.1.
            cfdi = re.sub(r'([cC]arta[pP]orte)30', r'\g<1>31', str(cfdi))

        cfdi_infos = self.env['l10n_mx_edi.document']._decode_cfdi_attachment(cfdi)
        cfdi_infos['cfdi_node'].attrib['Sello'] = certificate_sudo._sign(cfdi_infos['cadena'], formatting='base64')

        # -- clean schema locations --
        xsi_ns = cfdi_infos['cfdi_node'].nsmap['xsi']
        schema_locations = cfdi_infos['cfdi_node'].attrib[f"{{{xsi_ns}}}schemaLocation"].split()
        schema_parts = {ns: location for ns, location in zip(schema_locations[::2], schema_locations[1::2]) if ns in cfdi_infos['cfdi_node'].nsmap.values()}
        for ns in cfdi_infos['cfdi_node'].nsmap:
            if ns != 'xsi' and not cfdi_infos['cfdi_node'].xpath(f'//{ns}:*', namespaces=cfdi_infos['cfdi_node'].nsmap):
                schema_parts.pop(cfdi_infos['cfdi_node'].nsmap[ns])
        cfdi_infos['cfdi_node'].attrib[f'{{{xsi_ns}}}schemaLocation'] = ' '.join(f"{ns} {location}" for ns, location in schema_parts.items())

        # Clean up unused namespaces
        etree.cleanup_namespaces(cfdi_infos['cfdi_node'], keep_ns_prefixes=['xsi'])

        cfdi_str = self.env['l10n_mx_edi.document']._convert_xml_to_attachment_data(cfdi_infos['cfdi_node'])

        # == Check credentials ==
        pac_name = root_company.l10n_mx_edi_pac
        credentials = getattr(self.env['l10n_mx_edi.document'], f'_get_{pac_name}_credentials')(root_company)
        if credentials.get('errors'):
            on_failure(
                "\n".join(credentials['errors']),
                cfdi_filename=cfdi_filename,
                cfdi_str=cfdi_str,
            )
            if self._can_commit():
                self._cr.commit()
            return

        # == Check PAC ==
        sign_results = getattr(self.env['l10n_mx_edi.document'], f'_{pac_name}_sign')(credentials, cfdi_str)
        if sign_results.get('errors'):
            on_failure(
                "\n".join(sign_results['errors']),
                cfdi_filename=cfdi_filename,
                cfdi_str=cfdi_str,
            )
            if self._can_commit():
                self._cr.commit()
            return

        # == Success ==
        on_success(cfdi_values, cfdi_filename, sign_results['cfdi_str'], populate_return=populate_return)

        if self._can_commit():
            self._cr.commit()

    def _cancel_api(self, company, cancel_reason, on_failure, on_success):
        """ Common way to cancel a document.

        :param company:         The company.
        :param cancel_reason:   The reason for this cancel.
        :param on_failure:      The method to call in case of failure.
        :param on_success:      The method to call in case of success.
        """
        self.ensure_one()

        cfdi_values = self.env['l10n_mx_edi.document']._get_company_cfdi_values(company)
        if cfdi_values.get('errors'):
            on_failure("\n".join(cfdi_values['errors']))
            if self._can_commit():
                self._cr.commit()
            return

        root_company = cfdi_values['root_company']

        self.env['l10n_mx_edi.document']._add_certificate_cfdi_values(cfdi_values)
        if cfdi_values.get('errors'):
            on_failure("\n".join(cfdi_values['errors']))
            if self._can_commit():
                self._cr.commit()
            return

        # == Check credentials ==
        pac_name = root_company.l10n_mx_edi_pac
        credentials = getattr(self.env['l10n_mx_edi.document'], f'_get_{pac_name}_credentials')(root_company)
        if credentials.get('errors'):
            on_failure("\n".join(credentials['errors']))
            if self._can_commit():
                self._cr.commit()
            return

        # == Check PAC ==
        substitution_doc = self._get_substitution_document()
        cancel_uuid = substitution_doc.attachment_uuid
        cancel_results = getattr(self.env['l10n_mx_edi.document'], f'_{pac_name}_cancel')(
            cfdi_values,
            credentials,
            self.attachment_uuid,
            cancel_reason,
            cancel_uuid=cancel_uuid,
        )
        if cancel_results.get('errors'):
            on_failure("\n".join(cancel_results['errors']))
            if self._can_commit():
                self._cr.commit()
            return

        # == Success ==
        on_success()

        if self._can_commit():
            self._cr.commit()

    # -------------------------------------------------------------------------
    # SAT
    # -------------------------------------------------------------------------

    def _fetch_sat_status(self, supplier_rfc, customer_rfc, total, uuid):
        url = 'https://consultaqr.facturaelectronica.sat.gob.mx/ConsultaCFDIService.svc?wsdl'
        params = f'?id={uuid or ""}' \
                 f'&re={tools.html_escape(supplier_rfc or "")}' \
                 f'&rr={tools.html_escape(customer_rfc or "")}' \
                 f'&tt={total or 0.0}'
        transport = Transport(timeout=20)

        try:
            client = Client(wsdl=url, transport=transport)
            response = client.service.Consulta(params)
            fetched_state = response['Estado'] if hasattr(response, 'Estado') else ''
            # pylint: disable=broad-except
        except Exception as e:
            return {
                'error': _("Failure during update of the SAT status: %s", str(e)),
                'value': 'error',
            }

        if fetched_state == 'Vigente':
            return {'value': 'valid'}
        elif fetched_state == 'Cancelado':
            return {'value': 'cancelled'}
        elif fetched_state == 'No Encontrado':
            return {'value': 'not_found'}
        else:
            return {'value': 'not_defined'}

    def _update_document_sat_state(self, sat_state, error=None):
        """ Update the current document with the newly fetched state from the SAT.

        :param sat_state: The SAT state returned by '_fetch_sat_status'.
        :param error:       In case of error, the message returned by the SAT.
        """
        self.ensure_one()

        if self.move_id and self.state in ('invoice_sent', 'invoice_cancel', 'invoice_cancel_requested', 'invoice_received'):
            self.move_id._l10n_mx_edi_cfdi_invoice_update_sat_state(self, sat_state, error=error)
            return True
        elif self.state in ('payment_sent', 'payment_cancel'):
            if self.move_id:
                self.move_id._l10n_mx_edi_cfdi_payment_update_sat_state(self, sat_state, error=error)
            return True
        else:
            source_records = self._get_source_records()
            if source_records and self.state in ('ginvoice_sent', 'ginvoice_cancel'):
                source_records._l10n_mx_edi_cfdi_global_invoice_update_document_sat_state(self, sat_state, error=error)
                return True
        return False

    def _update_sat_state(self):
        """ Update the SAT state.

        :param: cadena_tfd:     The path to the cadenaoriginal_TFD xslt file.
        :param: cadena:         The path to the cadenaoriginal xslt file.
        """
        self.ensure_one()

        cfdi_infos = self.env['l10n_mx_edi.document']._decode_cfdi_attachment(self.attachment_id.raw)
        if not cfdi_infos:
            return

        sat_results = self._fetch_sat_status(
            cfdi_infos['supplier_rfc'],
            cfdi_infos['customer_rfc'],
            cfdi_infos['amount_total'],
            cfdi_infos['uuid'],
        )

        if self.sat_state == sat_results['value']:
            # force update write_date
            self.sat_state = sat_results['value']
        else:
            self._update_document_sat_state(sat_results['value'], error=sat_results.get('error'))

        if self._can_commit():
            self._cr.commit()

        return sat_results

    @api.model
    def _get_update_sat_status_domains(self, from_cron=True):
        results = [
            [
                ('state', 'in', (
                    'ginvoice_sent',
                    'invoice_sent',
                    'payment_sent',
                    'ginvoice_cancel',
                    'invoice_cancel',
                    'invoice_cancel_requested',
                    'payment_cancel',
                )),
                ('sat_state', 'not in', ('valid', 'cancelled', 'skip')),
            ],
            # always show the 'Update SAT' button for imports, since originator may cancel the invoice anytime
            [
                ('state', '=', 'invoice_received'),
                ('move_id.state', '=', 'posted'),
            ],
        ]

        # The user still can cancel the document from the SAT portal. In that case, we need
        # to display the SAT button just in case. However, we don't want to retroactively check
        # all passed documents so this is happening only for the form view and not for the CRON.
        if not from_cron:
            results.extend([
                [
                    ('state', 'in', ('invoice_sent', 'invoice_cancel_requested', 'payment_sent')),
                    ('move_id.l10n_mx_edi_cfdi_state', '=', 'sent'),
                    ('sat_state', '=', 'valid'),
                ],
                [
                    ('state', '=', 'ginvoice_sent'),
                    ('invoice_ids', 'any', [('l10n_mx_edi_cfdi_state', '=', 'global_sent')]),
                    ('sat_state', '=', 'valid'),
                ],
            ])

        return results

    @api.model
    def _get_update_sat_status_domain(self, extra_domain=None, from_cron=True):
        """ Build the domain to filter the documents that need an update from the SAT.

        :param extra_domain:    An optional extra domain to be injected when searching for documents to update.
        :param from_cron:       Indicate if the call is from the CRON or not.
        :return:                An odoo domain.
        """
        domain = expression.OR(self._get_update_sat_status_domains(from_cron=from_cron))
        if extra_domain:
            domain = expression.AND([domain, extra_domain])
        return domain

    @api.model
    def _fetch_and_update_sat_status(self, batch_size=100, extra_domain=None):
        """ Call the SAT to know if the invoice is available government-side or if the invoice has been cancelled.
        In the second case, the cancellation could be done Odoo-side and then we need to check if the SAT is up-to-date,
        or could be done manually government-side forcing Odoo to update the invoice's state.

        :param batch_size:      The maximum size of the batch of documents to process to avoid timeout.
        :param extra_domain:    An optional extra domain to be injected when searching for documents to update.
        """
        domain = self._get_update_sat_status_domain(extra_domain=extra_domain)
        domain = expression.AND([domain, [('write_date', '>=', fields.Date.today() - timedelta(days=60))]])
        documents = self.search(domain, limit=batch_size + 1, order='write_date, id')

        for document in documents[:batch_size]:
            document._update_sat_state()

        if len(documents) == batch_size:
            self.env.ref('l10n_mx_edi.ir_cron_update_pac_status_invoice')._trigger()
