# Part of Odoo. See LICENSE file for full copyright and licensing details.
import base64
import logging
from contextlib import suppress
from lxml import etree, html
from markupsafe import Markup
from odoo import api, fields, models
from odoo.exceptions import UserError
from odoo.tools.translate import _


_logger = logging.getLogger(__name__)


class AccountMove(models.Model):
    _inherit = 'account.move'

    l10n_cl_aec_attachment_file = fields.Binary(copy=False, attachment=True)
    l10n_cl_aec_attachment_id = fields.Many2one(
        comodel_name='ir.attachment',
        compute=lambda self: self._compute_linked_attachment_id(
            'l10n_cl_aec_attachment_id', 'l10n_cl_aec_attachment_file'), string="AEC Attachment")
    l10n_cl_aec_entry_ids = fields.One2many('account.move', 'l10n_cl_yielded_invoice_id', string='AEC Entries', copy=False)
    l10n_cl_yielded_invoice_id = fields.Many2one('account.move', string='Yielded Invoice')
    l10n_cl_aec_yielded = fields.Selection([('to_yield', 'To Yield'), ('yielded', 'Yielded')],
                                           string='Yield Status', compute='_compute_l10n_cl_yielded_status')

    def l10n_cl_button_yield_entry(self):
        self.ensure_one()
        return self.l10n_cl_aec_entry_ids._get_records_action(
            name=_('Yield Entries')
        )

    def l10n_cl_yield_invoice(self):
        self.ensure_one()
        return self.l10n_cl_yielded_invoice_id._get_records_action(
            name=_('Yielded Invoice')
        )

    @api.depends('l10n_cl_aec_entry_ids')
    def _compute_l10n_cl_yielded_status(self):
        for move in self:
            if (len(move.l10n_cl_aec_entry_ids.filtered(lambda x: x.state == 'posted')) == 1 and
                    move.payment_state == 'paid'):
                move.l10n_cl_aec_yielded = 'to_yield' \
                    if move.l10n_cl_aec_entry_ids.filtered(lambda x: x.l10n_cl_dte_status != 'accepted') else 'yielded'
            else:
                move.l10n_cl_aec_yielded = False

    def _post(self, soft=True):
        if self.filtered(lambda x: x._l10n_cl_is_aec_move() and x.posted_before):
            raise UserError(_('You cannot post an AEC posted before. You should cancel and create'
                              'a new one from the related invoice.'))
        res = super()._post(soft=soft)
        return res

    def _parse_response(self, response):
        # This method is to ensure to find the response in the correct encoding
        try:
            return {'result': etree.fromstring(response), 'type': 'xml'}
        except etree.XMLSyntaxError as e:
            _logger.error(f'XMLSyntaxError: {e}')
            _logger.error(f'Response: {response}')
            if isinstance(response, bytes):
                for encoding in ['utf-8', 'iso-8859-1', 'windows-1252']:
                    with suppress(UnicodeDecodeError, etree.XMLSyntaxError):
                        return {'result': etree.fromstring(response.decode(encoding)), 'type': 'xml'}
        # If we arrive here, we don't have an XML response, and probably there is a
        # message with a warning or similar, which we should put on chatter
        try:
            return {'result': html.fromstring(response), 'type': 'html'}
        except Exception as e:
            _logger.error(f"Parse error as HTML: {e}")
            return {'result': None, 'type': None}

    def _get_fields_to_detach(self):
        # EXTENDS account
        fields_list = super()._get_fields_to_detach()
        fields_list.append('l10n_cl_aec_attachment_file')
        return fields_list

    def _l10n_cl_is_aec_move(self):
        return self.move_type == 'entry' and self.l10n_cl_aec_attachment_id

    def l10n_cl_send_dte_to_sii(self, retry_send=True):
        if not self._l10n_cl_is_aec_move():
            return super().l10n_cl_send_dte_to_sii(retry_send)
        digital_signature_sudo = self.company_id.sudo()._get_digital_signature(user_id=self.env.user.id)
        if self.company_id.l10n_cl_dte_service_provider == 'SIIDEMO':
            self.message_post(body=_("AEC is simulated as 'accepted' in DEMO mode."))
            self.l10n_cl_dte_status = 'accepted'
            return None
        params = {
            'emailNotif': self.company_id.l10n_cl_dte_email,
            'rutCompany': self._l10n_cl_format_vat(self.company_id.vat)[:-2],
            'dvCompany': self._l10n_cl_format_vat(self.company_id.vat)[-1],
            'archivo': (
                self.l10n_cl_aec_attachment_id.name,
                base64.b64decode(self.l10n_cl_aec_attachment_file),
                'application/xml'),
        }
        response = self._send_xml_to_sii(
            self.company_id.l10n_cl_dte_service_provider,
            self.company_id.website,
            params,
            digital_signature_sudo,
            post='/cgi_rtc/RTC/RTCAnotEnvio.cgi'
        )
        if not response:
            digital_signature_sudo.last_token = False
            return None
        analyze_response = self._parse_response(response)
        if analyze_response['type'] == 'html':
            self.message_post(body=_('WARNING: Message from SII was: %s', analyze_response['result']))
            digital_signature_sudo.last_token = False
            return None
        elif analyze_response['type'] is None:
            self.message_post(body=_('The SII did not answered properly. Please try again'))
            digital_signature_sudo.last_token = False
            return None
        response_parsed = analyze_response['result']
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
        elif sii_response_status == '0':
            self.l10n_cl_dte_status = 'ask_for_status'
        else:
            self.l10n_cl_dte_status = 'rejected'
        self.message_post(body=_('DTE has been sent to SII with response: %s.',
                                 self._l10n_cl_get_sii_reception_status_message(sii_response_status)))

    def l10n_cl_verify_dte_status(self, send_dte_to_partner=True):
        if not self._l10n_cl_is_aec_move():
            return super().l10n_cl_verify_dte_status(send_dte_to_partner)

        digital_signature = self.company_id.sudo()._get_digital_signature(user_id=self.env.user.id)
        response = self._get_aec_send_status(
            self.company_id.l10n_cl_dte_service_provider,
            self.l10n_cl_sii_send_ident,
            digital_signature)
        if not response:
            self.l10n_cl_dte_status = 'ask_for_status'
            digital_signature.last_token = False
            return None
        response_parsed = etree.fromstring(response.encode('utf-8'))
        if response_parsed.findtext(
                '{http://www.sii.cl/XMLSchema}RESP_HDR/{http://www.sii.cl/XMLSchema}ESTADO') in ['3', '4']:
            digital_signature.last_token = False
            _logger.error('Token is invalid.')
            return None
        self.l10n_cl_dte_status = self._analyze_aec_sii_result(response_parsed)
        self.message_post(
            body=_('Asking for DTE status with response:') +
                 Markup('<br /><li><b>%s</b>: %s</li><li><b>%s</b>: %s</li>') % (
                     _('Sending status'),
                     response_parsed.findtext('{http://www.sii.cl/XMLSchema}RESP_BODY/ESTADO_ENVIO'),
                     _('Description'),
                     response_parsed.findtext('{http://www.sii.cl/XMLSchema}RESP_BODY/DESC_ESTADO')))

    def _l10n_cl_render_and_sign_xml(
            self, template, values, doc_id, doc_type, digital_signature, without_xml_declaration=True):
        rendered_xml = self.env['ir.qweb']._render(template, values)
        return self._sign_full_xml(
            rendered_xml, digital_signature, doc_id, doc_type, without_xml_declaration=without_xml_declaration)

    def _validate_aec_creation_conditions(self):
        aec_codes = ['33', '34', '46', '43']
        if not self.company_id.l10n_cl_factoring_journal_id:
            raise UserError(_('There is no journal configured for factoring. '
                              'Please go to the company settings and set a journal'))
        if not self.company_id.l10n_cl_factoring_counterpart_account_id:
            raise UserError(_('There is no counterpart account configured for factoring. '
                              'Please go to the company settings and set a counterpart account'))
        if not self.partner_id.email:
            raise UserError(_('The Factoring company %s does not have an email', self.partner_id.name))
        if not self.partner_id.l10n_cl_dte_email:
            raise UserError(
                _('The partner has no DTE email defined. This is mandatory for electronic invoicing.'))
        if not self.partner_id.vat:
            raise UserError(_('The Factoring company %s does not have a RUT number', self.partner_id.name))
        if self.partner_id.country_id.code != 'CL':
            raise UserError(_('The Factoring company %s is not from Chile. You cannot use this factoring method '
                              'for a foreign factoring company', self.partner_id.name))
        if not self.company_id.partner_id.city:
            raise UserError(_('There is no city configured in your partner company. This is mandatory for AEC. '
                              'Please go to your partner company and set the city.', self.partner_id.name))
        if not self.company_id.partner_id.street:
            raise UserError(_('There is no address configured in your partner company. '
                              'This is mandatory for AEC. Please go to the partner company and set the address'))
        non_factoring_invoices = self.filtered(lambda x: x.l10n_latam_document_type_id.code not in aec_codes)
        if non_factoring_invoices:
            raise UserError(_('These invoices cannot be factored: %s', ', '.join(
                non_factoring_invoices.mapped('name'))))
        non_accepted_invoices = self.filtered(lambda x: x.l10n_cl_dte_status not in ['accepted', 'objected'])
        if non_accepted_invoices:
            raise UserError(_('These invoices cannot be factored until they are accepted by SII: %s', ', '.join(
                non_accepted_invoices.mapped('name'))))
        already_yielded = self.filtered(lambda x: x.l10n_cl_aec_yielded in ['yielded', 'to_yield'])
        if already_yielded:
            raise UserError(_('Selected documents are already yielded or in process: %s.', ', '.join(
                already_yielded.mapped('name'))))
        in_payment_or_paid = self.filtered(lambda x: x.payment_state in ['in_payment', 'paid'])
        if in_payment_or_paid:
            raise UserError(_('Selected documents are in payment state or already paid: %s.', ', '.join(
                in_payment_or_paid.mapped('name'))))

    def action_l10n_cl_create_aec(self):
        self._validate_aec_creation_conditions()  # Configuration and factoring company validations
        return self.env['ir.actions.actions']._for_xml_id('l10n_cl_edi_factoring.action_create_aec_wizard')
