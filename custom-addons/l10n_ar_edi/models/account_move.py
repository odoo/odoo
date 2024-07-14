# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import fields, models, api, _
from odoo.exceptions import UserError, RedirectWarning
from odoo.tools.float_utils import float_repr, float_round
from odoo.tools import html2plaintext, plaintext2html
from odoo.tools.sql import column_exists, create_column
from datetime import datetime
from . import afip_errors
import re
import logging
import base64
import json
from markupsafe import Markup


_logger = logging.getLogger(__name__)

WS_DATE_FORMAT = {'wsfe': '%Y%m%d', 'wsfex': '%Y%m%d', 'wsbfe': '%Y%m%d'}


class AccountMove(models.Model):

    _inherit = "account.move"

    def _auto_init(self):
        if not column_exists(self.env.cr, "account_move", "l10n_ar_fce_transmission_type"):
            # Create the column to avoid computation during installation
            # Default value is set to NULL because it is initiated that way
            create_column(self.env.cr, "account_move", "l10n_ar_fce_transmission_type", "varchar")
        return super()._auto_init()

    l10n_ar_afip_auth_mode = fields.Selection([('CAE', 'CAE'), ('CAI', 'CAI'), ('CAEA', 'CAEA')],
        string='AFIP Authorization Mode', copy=False,
        help="This is the type of AFIP Authorization, depending on the way that the invoice is created"
        " the mode will change:\n\n"
        " * CAE (Electronic Authorization Code): Means that is an electronic invoice. If you validate a customer invoice"
        " this field will be autofill with CAE option. Also, if you trying to verify in AFIP an electronic vendor bill"
        " you can set this option\n"
        " * CAI (Printed Authorization Code): Means that is a pre-printed invoice. With this option set you can"
        " register and verify in AFIP pre-printed vendor bills\n"
        " * CAEA (Anticipated Electronic Authorization Code): Means that is an electronic invoice. This kind of invoices"
        " are generated using a pre ganerated code by AFIP for companies that have a massive invoicing by month so they"
        " can pre process all the invoices of the fortnight in one operation with one unique CAEA. Select this option"
        " only when verifying in AFIP a vendor bill that have CAEA (invoices with CAEA will not have CAE)")
    l10n_ar_afip_auth_code = fields.Char('Authorization Code', copy=False, size=24, help="Argentina: authorization code given by AFIP after electronic invoice is created and valid.")
    l10n_ar_afip_auth_code_due = fields.Date('Authorization Due date', copy=False,
        help="Argentina: The Due Date of the Invoice given by AFIP.")
    l10n_ar_afip_qr_code = fields.Char(compute='_compute_l10n_ar_afip_qr_code', string='AFIP QR Code',
        help='This QR code is mandatory by the AFIP in the electronic invoices when this ones are printed.')

    # electronic invoice fields
    l10n_ar_afip_xml_request = fields.Text(string='XML Request', copy=False, readonly=True, groups="base.group_system")
    l10n_ar_afip_xml_response = fields.Text(string='XML Response', copy=False, readonly=True, groups="base.group_system")
    l10n_ar_afip_result = fields.Selection([('A', 'Accepted in AFIP'), ('O', 'Accepted in AFIP with Observations')], 'Result',
        copy=False, help="Argentina: Result of the electronic invoice request to the AFIP web service.", tracking=True)
    l10n_ar_afip_ws = fields.Selection(related="journal_id.l10n_ar_afip_ws")

    # fields used to check invoice is valid on AFIP
    l10n_ar_afip_verification_type = fields.Selection(
        [('not_available', 'Not Available'), ('available', 'Available'), ('required', 'Required')],
        compute='_compute_l10n_ar_afip_verification_type')
    l10n_ar_afip_verification_result = fields.Selection([('A', 'Approved'), ('O', 'Observed'), ('R', 'Rejected')],
        string='AFIP Verification result', copy=False, readonly=True)

    # FCE related fields
    l10n_ar_afip_fce_is_cancellation = fields.Boolean(string='FCE: Is Cancellation?',
        copy=False, help='Argentina: When informing a MiPyMEs (FCE) debit/credit notes in AFIP it is required to send information about whether the'
        ' original document has been explicitly rejected by the buyer. More information here'
        ' http://www.afip.gob.ar/facturadecreditoelectronica/preguntasFrecuentes/emisor-factura.asp')
    l10n_ar_fce_transmission_type = fields.Selection(
        [('SCA', 'SCA - TRANSFERENCIA AL SISTEMA DE CIRCULACION ABIERTA'), ('ADC', 'ADC - AGENTE DE DEPOSITO COLECTIVO')],
        string='FCE: Transmission Option', compute="_compute_l10n_ar_fce_transmission_type", store=True, readonly=False,
        help="This field only need to be set when you are reporting a MiPyME FCE documents. Default value can be set in the Accouting Settings")

    # Compute methods

    @api.depends('l10n_ar_afip_result')
    def _compute_show_reset_to_draft_button(self):
        """
            EXTENDS 'account.move'
            When the AFIP approved the move, don't show the reset to draft button
        """
        super()._compute_show_reset_to_draft_button()
        self.filtered(lambda move: move.l10n_ar_afip_result == "A").show_reset_to_draft_button = False

    @api.depends('l10n_latam_document_type_id')
    def _compute_l10n_ar_fce_transmission_type(self):
        """ Automatically set the default value on the l10n_ar_fce_transmission_type field if the invoice is a mipyme
        one with the default value set in the company """
        mipyme_fce_docs = self.filtered(lambda x: x.country_code == 'AR' and x._is_mipyme_fce())
        for rec in mipyme_fce_docs.filtered(lambda x: not x.l10n_ar_fce_transmission_type):
            if rec.company_id.l10n_ar_fce_transmission_type:
                rec.l10n_ar_fce_transmission_type = rec.company_id.l10n_ar_fce_transmission_type
        remaining = self - mipyme_fce_docs
        remaining.l10n_ar_fce_transmission_type = False

    @api.depends('l10n_ar_afip_auth_code')
    def _compute_l10n_ar_afip_qr_code(self):
        """ Method that generates the QR code with the electronic invoice info taking into account RG 4291 """
        with_qr_code = self.filtered(lambda x: x.l10n_ar_afip_auth_mode in ['CAE', 'CAEA'] and x.l10n_ar_afip_auth_code)
        for rec in with_qr_code:
            data = {
                'ver': 1,
                'fecha': str(rec.invoice_date),
                'cuit': int(rec.company_id.partner_id.l10n_ar_vat),
                'ptoVta': rec.journal_id.l10n_ar_afip_pos_number,
                'tipoCmp': int(rec.l10n_latam_document_type_id.code),
                'nroCmp': int(self._l10n_ar_get_document_number_parts(
                    rec.l10n_latam_document_number, rec.l10n_latam_document_type_id.code)['invoice_number']),
                'importe': float_round(rec.amount_total, precision_digits=2, rounding_method='DOWN'),
                'moneda': rec.currency_id.l10n_ar_afip_code,
                'ctz': float_round(rec.l10n_ar_currency_rate, precision_digits=6, rounding_method='DOWN'),
                'tipoCodAut': 'E' if rec.l10n_ar_afip_auth_mode == 'CAE' else 'A',
                'codAut': int(rec.l10n_ar_afip_auth_code),
            }

            commercial_partner_id = rec.commercial_partner_id
            if commercial_partner_id.country_id and commercial_partner_id.country_id.code != 'AR':
                nro_doc_rec = int(
                    commercial_partner_id.country_id.l10n_ar_legal_entity_vat
                    if commercial_partner_id.is_company else commercial_partner_id.country_id.l10n_ar_natural_vat)
            else:
                nro_doc_rec = commercial_partner_id._get_id_number_sanitize() or False

            data.update({'nroDocRec': nro_doc_rec or 0})
            if commercial_partner_id.l10n_latam_identification_type_id:
                data.update({'tipoDocRec': int(rec._get_partner_code_id(commercial_partner_id))})
            # For more info go to https://www.afip.gob.ar/fe/qr/especificaciones.asp
            rec.l10n_ar_afip_qr_code = 'https://www.afip.gob.ar/fe/qr/?p=%s' % base64.b64encode(json.dumps(
                data).encode()).decode('ascii')

        remaining = self - with_qr_code
        remaining.l10n_ar_afip_qr_code = False

    @api.depends('l10n_latam_document_type_id', 'company_id')
    def _compute_l10n_ar_afip_verification_type(self):
        """ Method that tell us if the invoice/vendor bill can be verified in AFIP """
        verify_codes = ["1", "2", "3", "4", "5", "6", "7", "8", "9", "10", "11", "12", "13", "15", "19", "20", "21",
                        "49", "51", "52", "53", "54", "60", "61", "63", "64"]
        available_to_verify = self.filtered(
            lambda x: x.l10n_latam_document_type_id and x.l10n_latam_document_type_id.code in verify_codes)
        for rec in available_to_verify:
            rec.l10n_ar_afip_verification_type = rec.company_id.l10n_ar_afip_verification_type
        remaining = self - available_to_verify
        remaining.l10n_ar_afip_verification_type = 'not_available'

    # Buttons
    def _is_dummy_afip_validation(self):
        self.ensure_one()
        return self.company_id._get_environment_type() == 'testing' and \
            not self.company_id.sudo().l10n_ar_afip_ws_crt or not self.company_id.sudo().l10n_ar_afip_ws_key

    def _post(self, soft=True):
        """ After validate the invoice we then validate in AFIP. The last thing we do is request the cae because if an
        error occurs after CAE requested, the invoice has been already validated on AFIP """
        ar_invoices = self.filtered(lambda x: x.is_invoice() and x.company_id.account_fiscal_country_id.code == "AR")
        sale_ar_invoices = ar_invoices.filtered(lambda x: x.move_type in ['out_invoice', 'out_refund'])

        # Verify only Vendor bills (only when verification is configured as 'required')
        (ar_invoices - sale_ar_invoices)._l10n_ar_check_afip_auth_verify_required()

        # Send invoices to AFIP and get the return info
        ar_edi_invoices = ar_invoices.filtered(lambda x: x.journal_id.l10n_ar_afip_ws)
        validated = error_invoice = self.env['account.move']
        for inv in ar_edi_invoices:

            # If we are on testing environment and we don't have certificates we validate only locally.
            # This is useful when duplicating the production database for training purpose or others
            if inv._is_dummy_afip_validation() and not inv.l10n_ar_afip_auth_code:
                inv._dummy_afip_validation()
                validated += super(AccountMove, inv)._post(soft=soft)
                continue

            client, auth, transport = inv.company_id._l10n_ar_get_connection(inv.journal_id.l10n_ar_afip_ws)._get_client(return_transport=True)
            validated += super(AccountMove, inv)._post(soft=soft)
            return_info = inv._l10n_ar_do_afip_ws_request_cae(client, auth, transport)
            if return_info:
                error_invoice = inv
                validated -= inv
                break

            # If we get CAE from AFIP then we make commit because we need to save the information returned by AFIP
            # in Odoo for consistency, this way if an error ocurrs later in another invoice we will have the ones
            # correctly validated in AFIP in Odoo (CAE, Result, xml response/request).
            if not self.env.context.get('l10n_ar_invoice_skip_commit'):
                self._cr.commit()

        if error_invoice:
            if error_invoice.exists():
                msg = _('We couldn\'t validate the document "%s" (Draft Invoice *%s) in AFIP',
                    error_invoice.partner_id.name, error_invoice.id)
            else:
                msg = _('We couldn\'t validate the invoice in AFIP.')
            msg += _('This is what we get:\n%s\n\nPlease make the required corrections and try again', return_info)

            # if we've already validate any invoice, we've commit and we want to inform which invoices were validated
            # which one were not and the detail of the error we get. This ins neccesary because is not usual to have a
            # raise with changes commited on databases
            if validated:
                unprocess = self - validated - error_invoice
                msg = _(
                    """Some documents where validated in AFIP but as we have an error with one document the batch validation was stopped

* These documents were validated:
%(validate_invoices)s
* These documents weren\'t validated:
%(invalide_invoices)s
""",
                    validate_invoices="\n   * ".join(validated.mapped('name')),
                    invalide_invoices="\n   * ".join([
                        _("%s: %r amount %s", item.display_name, item.partner_id.name, item.amount_total_signed) for item in unprocess
                    ])
                )
            raise UserError(msg)

        return validated + super(AccountMove, self - ar_edi_invoices)._post(soft=soft)

    def l10n_ar_verify_on_afip(self):
        """ This method let us to connect to AFIP using WSCDC webservice to verify if a vendor bill is valid on AFIP """
        for inv in self:
            if not inv.l10n_ar_afip_auth_mode or not inv.l10n_ar_afip_auth_code:
                raise UserError(_('Please set AFIP Authorization Mode and Code to continue!'))

            # get Issuer and Receptor depending on the document type
            issuer, receptor = (inv.commercial_partner_id, inv.company_id.partner_id) \
                if inv.move_type in ['in_invoice', 'in_refund'] else (inv.company_id.partner_id, inv.commercial_partner_id)
            issuer_vat = issuer.ensure_vat()

            receptor_identification_code = receptor.l10n_latam_identification_type_id.l10n_ar_afip_code or '99'
            receptor_id_number = (receptor_identification_code and str(receptor._get_id_number_sanitize()))

            if inv.l10n_latam_document_type_id.l10n_ar_letter in ['A', 'M'] and receptor_identification_code != '80' or not receptor_id_number:
                raise UserError(_('For type A and M documents the receiver identification is mandatory and should be VAT'))

            document_parts = self._l10n_ar_get_document_number_parts(inv.l10n_latam_document_number, inv.l10n_latam_document_type_id.code)
            if not document_parts['point_of_sale'] or not document_parts['invoice_number']:
                raise UserError(_('Point of sale and document number are required!'))
            if not inv.l10n_latam_document_type_id.code:
                raise UserError(_('No document type selected or document type is not available for validation!'))
            if not inv.invoice_date:
                raise UserError(_('Invoice Date is required!'))

            connection = self.company_id._l10n_ar_get_connection('wscdc')
            client, auth = connection._get_client()
            response = client.service.ComprobanteConstatar(auth, {
                'CbteModo': inv.l10n_ar_afip_auth_mode,
                'CuitEmisor': issuer_vat,
                'PtoVta': document_parts['point_of_sale'],
                'CbteTipo': inv.l10n_latam_document_type_id.code,
                'CbteNro': document_parts['invoice_number'],
                'CbteFch': inv.invoice_date.strftime('%Y%m%d'),
                'ImpTotal': float_repr(inv.amount_total, precision_digits=2),
                'CodAutorizacion': inv.l10n_ar_afip_auth_code,
                'DocTipoReceptor': receptor_identification_code,
                'DocNroReceptor': receptor_id_number})
            inv.write({'l10n_ar_afip_verification_result': response.Resultado})
            if response.Observaciones or response.Errors:
                inv.message_post(body=_('AFIP authorization verification result: %s%s', response.Observaciones, response.Errors))

    # Main methods

    def _l10n_ar_do_afip_ws_request_cae(self, client, auth, transport):
        """ Submits the invoice information to AFIP and gets a response of AFIP in return.

        If we receive a positive response from  AFIP then validate the invoice and save the returned information in the
        corresponding invoice fields:

        * CAE number (Authorization Electronic Code)
        * Authorization Type
        * XML Request
        * XML Response
        * Result (Approved, Aproved with Observations)

            NOTE: If there are observations we leave a message in the invoice message chart with the observation.

        If there are errors it means that the invoice has been Rejected by AFIP and we raise an user error with the
        processed info about the error and some hint about how to solve it. The invoice is not valided.
        """
        for inv in self.filtered(lambda x: x.journal_id.l10n_ar_afip_ws and not x.l10n_ar_afip_auth_code):
            afip_ws = inv.journal_id.l10n_ar_afip_ws
            errors = obs = events = ''
            request_data = False
            return_codes = []
            values = {}

            # We need to call a different method for every webservice type and assemble the returned errors if they exist
            if afip_ws == 'wsfe':
                ws_method = 'FECAESolicitar'
                request_data = inv.wsfe_get_cae_request(client)
                self._ws_verify_request_data(client, auth, ws_method, request_data)
                response = client.service[ws_method](auth, request_data)
                if response.FeDetResp:
                    result = response.FeDetResp.FECAEDetResponse[0]
                    if result.Observaciones:
                        obs = ''.join(['\n* Code %s: %s' % (ob.Code, ob.Msg) for ob in result.Observaciones.Obs])
                        return_codes += [str(ob.Code) for ob in result.Observaciones.Obs]
                    if result.Resultado == 'A':
                        values = {'l10n_ar_afip_auth_mode': 'CAE',
                                  'l10n_ar_afip_auth_code': result.CAE and str(result.CAE) or "",
                                  'l10n_ar_afip_auth_code_due': datetime.strptime(result.CAEFchVto, '%Y%m%d').date(),
                                  'l10n_ar_afip_result': result.Resultado}

                if response.Errors:
                    errors = ''.join(['\n* Code %s: %s' % (err.Code, err.Msg) for err in response.Errors.Err])
                    return_codes += [str(err.Code) for err in response.Errors.Err]
                if response.Events:
                    events = ''.join(['\n* Code %s: %s' % (evt.Code, evt.Msg) for evt in response.Events.Evt])
                    return_codes += [str(evt.Code) for evt in response.Events.Evt]

            elif afip_ws == 'wsfex':
                ws_method = 'FEXAuthorize'
                last_id = client.service.FEXGetLast_ID(auth).FEXResultGet.Id
                request_data = inv.wsfex_get_cae_request(last_id+1, client)
                self._ws_verify_request_data(client, auth, ws_method, request_data)
                response = client.service[ws_method](auth, request_data)
                result = response.FEXResultAuth
                if response.FEXErr.ErrCode != 0 or response.FEXErr.ErrMsg != 'OK':
                    errors = '\n* Code %s: %s' % (response.FEXErr.ErrCode, response.FEXErr.ErrMsg)
                    return_codes += [str(response.FEXErr.ErrCode)]
                if response.FEXEvents.EventCode != 0 or response.FEXEvents.EventMsg != 'Ok':
                    events = '\n* Code %s: %s' % (response.FEXEvents.EventCode, response.FEXEvents.EventMsg)
                    return_codes += [str(response.FEXEvents.EventCode)]

                if result:
                    if result.Motivos_Obs:
                        obs = '\n* Code ???: %s' % result.Motivos_Obs
                        return_codes += [result.Motivos_Obs]
                    if result.Reproceso == 'S':
                        return_codes += ['reprocess']
                    if result.Resultado != 'A':
                        if not errors:
                            return_codes += ['rejected']
                    else:
                        values = {'l10n_ar_afip_auth_mode': 'CAE',
                                  'l10n_ar_afip_auth_code': result.Cae,
                                  'l10n_ar_afip_auth_code_due': datetime.strptime(result.Fch_venc_Cae, '%Y%m%d').date(),
                                  'l10n_ar_afip_result': result.Resultado}

            elif afip_ws == 'wsbfe':
                ws_method = 'BFEAuthorize'
                last_id = client.service.BFEGetLast_ID(auth).BFEResultGet.Id
                request_data = inv.wsbfe_get_cae_request(last_id + 1, client)
                self._ws_verify_request_data(client, auth, ws_method, request_data)
                response = client.service[ws_method](auth, request_data)
                result = response.BFEResultAuth
                if response.BFEErr.ErrCode != 0 or response.BFEErr.ErrMsg != 'OK':
                    errors = '\n* Code %s: %s' % (response.BFEErr.ErrCode, response.BFEErr.ErrMsg)
                    return_codes += [str(response.BFEErr.ErrCode)]
                if response.BFEEvents.EventCode != 0 or response.BFEEvents.EventMsg:
                    events = '\n* Code %s: %s' % (response.BFEEvents.EventCode, response.BFEEvents.EventMsg)
                if result.Obs:
                    obs = result.Obs
                    return_codes += [result.Obs]
                if result.Reproceso == 'S':
                    return_codes += ['reprocess']
                if result.Resultado != 'A':
                    if not errors:
                        return_codes += ['rejected']
                else:
                    values = {'l10n_ar_afip_auth_code': result.Cae,
                              'l10n_ar_afip_auth_mode': 'CAE',
                              'l10n_ar_afip_result': result.Resultado if not obs else 'O',
                              'l10n_ar_afip_auth_code_due': datetime.strptime(result.Fch_venc_Cae, '%Y%m%d').date()}
            return_info = inv._prepare_return_msg(afip_ws, errors, obs, events, return_codes)
            afip_result = values.get('l10n_ar_afip_result')
            xml_response, xml_request = transport.xml_response, transport.xml_request
            if afip_result not in ['A', 'O']:
                if not self.env.context.get('l10n_ar_invoice_skip_commit'):
                    self.env.cr.rollback()
                if inv.exists():
                    # Only save the xml_request/xml_response fields if the invoice exists.
                    # It is possible that the invoice will rollback as well e.g. when it is automatically created:
                    #   * creating credit note with full reconcile option
                    #   * creating/validating an invoice from subscription/sales
                    inv.sudo().write({'l10n_ar_afip_xml_request': xml_request, 'l10n_ar_afip_xml_response': xml_response})
                if not self.env.context.get('l10n_ar_invoice_skip_commit'):
                    self.env.cr.commit()
                return return_info
            values.update(l10n_ar_afip_xml_request=xml_request, l10n_ar_afip_xml_response=xml_response)
            inv.sudo().write(values)
            if return_info:
                inv.message_post(body=Markup('<p><b>%s%s</b></p>') % (_('AFIP Messages'), plaintext2html(return_info, 'em')))

    # Helpers

    def _dummy_afip_validation(self):
        """ Only when we want to skip AFIP validation in testing environment. Fill the AFIP fields with dummy values in
        order to continue with the invoice validation without passing to AFIP validations
        """
        self.write({'l10n_ar_afip_auth_mode': 'CAE',
                    'l10n_ar_afip_auth_code': '68448767638166',
                    'l10n_ar_afip_auth_code_due': self.invoice_date,
                    'l10n_ar_afip_result': ''})
        self.message_post(body=_('Invoice validated locally because it is in a testing environment without testing certificate/keys'))

    def _l10n_ar_check_afip_auth_verify_required(self):
        """ If the company has set "Verify vendor bills: Required". it will check if the vendor bill has been verified
        in AFIP, if not will try to verify them.

        If the invoice is sucessfully verified in AFIP (result is Approved or Observations) then will let to continue
        with the post of the bill, if not then will raise an expection that will stop the post.
        """
        verification_missing = self.filtered(
            lambda x: x.move_type in ['in_invoice', 'in_refund'] and x.l10n_ar_afip_verification_type == 'required' and
            x.l10n_latam_document_type_id.country_id.code == "AR" and
            x.l10n_ar_afip_verification_result not in ['A', 'O'])
        try:
            verification_missing.l10n_ar_verify_on_afip()
        except Exception as error:
            _logger.error(repr(error))

        still_missing = verification_missing.filtered(lambda x: x.l10n_ar_afip_verification_result not in ['A', 'O'])
        if still_missing:
            if len(still_missing) > 1:
                raise UserError(_(
                    'We can not post these vendor bills in Odoo because the '
                    'AFIP verification fail: %s\nPlease verify in AFIP '
                    'manually and review the bill chatter for more information',
                    '\n * '.join(still_missing.mapped('display_name'))))
            raise UserError(_(
                'We can not post this vendor bill in Odoo because the AFIP '
                'verification fail: %s\nPlease verify in AFIP manually and '
                'review the bill chatter for more information',
                still_missing.display_name))

    def _is_mipyme_fce(self):
        """ True of False if the invoice is a mipyme document """
        self.ensure_one()
        return int(self.l10n_latam_document_type_id.code) in [201, 206, 211]

    def _is_mipyme_fce_refund(self):
        """ True of False if the invoice is a mipyme document """
        self.ensure_one()
        return int(self.l10n_latam_document_type_id.code) in [202, 203, 207, 208, 212, 213]

    def _due_payment_date(self):
        """ Due payment date only informed when concept = "services" or when invoice of type mipyme_fce """
        if self.l10n_ar_afip_concept != '1' and not self._is_mipyme_fce_refund() or self._is_mipyme_fce():
            return self.invoice_date_due or self.invoice_date
        return False

    def _service_dates(self):
        """ Service start and end date only set when concept is ony type "service" """
        if self.l10n_ar_afip_concept != '1':
            return self.l10n_ar_afip_service_start, self.l10n_ar_afip_service_end
        return False, False

    def _found_related_invoice(self):
        """ List related invoice information to fill associated voucher key for AFIP (CbtesAsoc).
        NOTE: for now we only get related document for debit and credit notes because, for eg, an invoice can not be
        related to another one, and that happens if you choose the modify option of the credit note wizard

        A mapping of which documents can be reported as related documents would be a better solution """
        self.ensure_one()
        if self.l10n_latam_document_type_id.internal_type == 'credit_note':
            return self.reversed_entry_id
        elif self.l10n_latam_document_type_id.internal_type == 'debit_note':
            return self.debit_origin_id
        else:
            return self.browse()

    def _get_tributes(self):
        """ Applies on wsfe web service """
        res = []
        not_vat_taxes = self.line_ids.filtered(lambda x: x.tax_line_id and x.tax_line_id.tax_group_id.l10n_ar_tribute_afip_code)
        for tribute in not_vat_taxes:
            base_imp = sum(self.invoice_line_ids.filtered(lambda x: x.tax_ids.filtered(
                lambda y: y.tax_group_id.l10n_ar_tribute_afip_code == tribute.tax_line_id.tax_group_id.l10n_ar_tribute_afip_code)).mapped(
                    'price_subtotal'))
            res.append({'Id': tribute.tax_line_id.tax_group_id.l10n_ar_tribute_afip_code,
                        'Alic': 0,
                        'Desc': tribute.tax_line_id.tax_group_id.name,
                        'BaseImp': float_repr(base_imp, precision_digits=2),
                        'Importe': float_repr(abs(tribute.amount_currency), precision_digits=2)})
        return res if res else None

    def _get_related_invoice_data(self):
        """ Applies on wsfe and wsfex web services """
        self.ensure_one()
        res = {}
        related_inv = self._found_related_invoice()
        afip_ws = self.journal_id.l10n_ar_afip_ws

        if not related_inv:
            return res

        # WSBFE_1035 We should only send CbtesAsoc if the invoice to validate has any of the next doc type codes
        if afip_ws == 'wsbfe' and \
           int(self.l10n_latam_document_type_id.code) not in [1, 2, 3, 6, 7, 8, 91, 201, 202, 203, 206, 207, 208]:
            return res

        wskey = {'wsfe': {'type': 'Tipo', 'pos_number': 'PtoVta', 'number': 'Nro', 'cuit': 'Cuit', 'date': 'CbteFch'},
                 'wsbfe': {'type': 'Tipo_cbte', 'pos_number': 'Punto_vta', 'number': 'Cbte_nro', 'cuit': 'Cuit', 'date': 'Fecha_cbte'},
                 'wsfex': {'type': 'Cbte_tipo', 'pos_number': 'Cbte_punto_vta', 'number': 'Cbte_nro', 'cuit': 'Cbte_cuit'}}

        res.update({wskey[afip_ws]['type']: related_inv.l10n_latam_document_type_id.code,
                    wskey[afip_ws]['pos_number']: related_inv.journal_id.l10n_ar_afip_pos_number,
                    wskey[afip_ws]['number']: self._l10n_ar_get_document_number_parts(
                        related_inv.l10n_latam_document_number, related_inv.l10n_latam_document_type_id.code)['invoice_number']})

        # WSFE_10151 send cuit of the issuer if type mipyme refund
        if self._is_mipyme_fce_refund() or afip_ws == 'wsfex':
            res.update({wskey[afip_ws]['cuit']: related_inv.company_id.partner_id._get_id_number_sanitize()})

        # WSFE_10158 send orignal invoice date on an mipyme document
        if afip_ws == 'wsfe' and (self._is_mipyme_fce() or self._is_mipyme_fce_refund()):
            res.update({wskey[afip_ws]['date']: related_inv.invoice_date.strftime(WS_DATE_FORMAT[afip_ws])})

        return res

    def _get_line_details(self):
        """ Used only in wsbfe and wsfex """
        self.ensure_one()
        details = []
        afip_ws = self.journal_id.l10n_ar_afip_ws
        for line in self.invoice_line_ids.filtered(lambda x: x.display_type not in ('line_section', 'line_note')):

            # Unit of measure of the product if it sale in a unit of measures different from has been purchase
            if not line.product_uom_id.l10n_ar_afip_code:
                raise UserError(_('No AFIP code in %s UOM', line.product_uom_id.name))

            Pro_umed = line.product_uom_id.l10n_ar_afip_code
            values = {
                'Pro_ds': line.name,
                'Pro_qty': line.quantity,
                'Pro_umed': Pro_umed,
                'Pro_precio_uni': line.price_unit,
            }

            # We compute bonus by substracting theoretical minus amount
            bonus = line.discount and \
                float_repr(line.price_unit * line.quantity - line.price_subtotal, precision_digits=2) or 0.0

            if afip_ws == 'wsbfe':
                if not line.product_id.uom_id.l10n_ar_afip_code:
                    raise UserError(_('No AFIP code in %s UOM', line.product_id.uom_id.name))

                vat_tax = line.tax_ids.filtered(lambda x: x.tax_group_id.l10n_ar_vat_afip_code)
                vat_taxes_amounts = vat_tax.compute_all(
                    line.price_unit, self.currency_id, line.quantity, product=line.product_id, partner=self.partner_id,
                    fixed_multiplicator=line.move_id.direction_sign,
                )

                line.product_id.product_tmpl_id._check_l10n_ar_ncm_code()
                values.update({'Pro_codigo_ncm': line.product_id.l10n_ar_ncm_code or '',
                               'Imp_bonif': bonus,
                               'Iva_id': vat_tax.tax_group_id.l10n_ar_vat_afip_code,
                               'Imp_total': vat_taxes_amounts['total_included']})
            elif afip_ws == 'wsfex':
                if Pro_umed != ['97', '99', '00']:
                    if line._get_downpayment_lines():
                        Pro_umed = '97'
                    elif line.price_unit < 0:
                        Pro_umed = '99'
                if Pro_umed in ['97', '99', '00']:
                    values = {
                        'Pro_ds': line.name,
                        'Pro_umed': Pro_umed,
                        'Pro_total_item': line.price_unit,
                        'Pro_qty': 0,
                        'Pro_precio_uni': 0,
                        'Pro_bonificacion': 0,
                    }
                values.update({'Pro_codigo': line.product_id.default_code or '',
                               'Pro_total_item': float_repr(line.price_subtotal, precision_digits=2),
                               'Pro_bonificacion': bonus})
            details.append(values)

        return details

    def _get_optionals_data(self):
        optionals = []
        # We add CBU to electronic credit invoice
        if self._is_mipyme_fce() and self.partner_bank_id.acc_type == 'cbu':
            optionals.append({'Id': 2101, 'Valor': self.partner_bank_id.acc_number})
        # We add FCE Is cancellation value only for refund documents
        if self._is_mipyme_fce_refund():
            optionals.append({'Id': 22, 'Valor': self.l10n_ar_afip_fce_is_cancellation and 'S' or 'N'})

        transmission_type = self.l10n_ar_fce_transmission_type
        if self._is_mipyme_fce() and transmission_type:
            optionals.append({'Id': 27, 'Valor': transmission_type})
        return optionals

    def _get_partner_code_id(self, partner):
        """ Return the AFIP code of the identification type of the partner.
        If not identification type and if the partner responsibility is Final Consumer return
        AFIP it_Sigd identification type (Sin Categoria / Venta Global)
        """
        partner_id_code = partner.l10n_latam_identification_type_id.l10n_ar_afip_code
        if partner_id_code:
            return partner_id_code
        final_consumer = self.env.ref('l10n_ar.res_CF')
        if partner.l10n_ar_afip_responsibility_type_id == final_consumer:
            return '99'
        return partner_id_code

    def _prepare_return_msg(self, afip_ws, errors, obs, events, return_codes):
        self.ensure_one()
        msg = ''
        if any([errors, obs, events]):
            if errors:
                msg += '\n' + _('AFIP Validation Error') + ': %s' % errors
            if obs and obs != ' ':
                msg += '\n' + _('AFIP Validation Observation') + ': %s' % obs
            if events:
                msg += '\n' + _('AFIP Validation Event') + ': %s' % events
            hint_msgs = []
            for code in return_codes:
                fix = afip_errors._hint_msg(code, afip_ws)
                if fix:
                    hint_msgs.append(fix)
            if hint_msgs:
                msg += '\n\n' + _('HINT') + ':\n\n * ' + '\n * '.join(hint_msgs)
        return msg

    def _ws_verify_request_data(self, client, auth, ws_method, request_data):
        """ Validate that all the request data sent is ok """
        try:
            client._Client__obj.create_message(client._Client__obj.service, ws_method, auth, request_data)
        except Exception as error:
            raise UserError(repr(error))

    # Prepare Request Data for webservices

    def wsfe_get_cae_request(self, client=None):
        self.ensure_one()
        partner_id_code = self._get_partner_code_id(self.commercial_partner_id)
        invoice_number = self._l10n_ar_get_document_number_parts(
            self.l10n_latam_document_number, self.l10n_latam_document_type_id.code)['invoice_number']
        amounts = self._l10n_ar_get_amounts()
        due_payment_date = self._due_payment_date()
        service_start, service_end = self._service_dates()

        related_invoices = self._get_related_invoice_data()
        vat_items = self._get_vat()
        for item in vat_items:
            if 'BaseImp' in item and 'Importe' in item:
                item['BaseImp'] = float_repr(item['BaseImp'], precision_digits=2)
                item['Importe'] = float_repr(item['Importe'], precision_digits=2)
        vat = partner_id_code and self.commercial_partner_id._get_id_number_sanitize()

        tributes = self._get_tributes()
        optionals = self._get_optionals_data()

        ArrayOfAlicIva = client.get_type('ns0:ArrayOfAlicIva')
        ArrayOfTributo = client.get_type('ns0:ArrayOfTributo')
        ArrayOfCbteAsoc = client.get_type('ns0:ArrayOfCbteAsoc')
        ArrayOfOpcional = client.get_type('ns0:ArrayOfOpcional')

        res = {'FeCabReq': {
                   'CantReg': 1, 'PtoVta': self.journal_id.l10n_ar_afip_pos_number, 'CbteTipo': self.l10n_latam_document_type_id.code},
               'FeDetReq': [{'FECAEDetRequest': {
                   'Concepto': int(self.l10n_ar_afip_concept),
                   'DocTipo': partner_id_code or 0,
                   'DocNro': vat and int(vat) or 0,
                   'CbteDesde': invoice_number,
                   'CbteHasta': invoice_number,
                   'CbteFch': self.invoice_date.strftime(WS_DATE_FORMAT['wsfe']),

                   'ImpTotal': float_repr(self.amount_total, precision_digits=2),
                   'ImpTotConc': float_repr(amounts['vat_untaxed_base_amount'], precision_digits=2),  # Not Taxed VAT
                   'ImpNeto': float_repr(amounts['vat_taxable_amount'], precision_digits=2),
                   'ImpOpEx': float_repr(amounts['vat_exempt_base_amount'], precision_digits=2),
                   'ImpTrib': float_repr(amounts['not_vat_taxes_amount'], precision_digits=2),
                   'ImpIVA': float_repr(amounts['vat_amount'], precision_digits=2),

                   # Service dates are only informed when AFIP Concept is (2,3)
                   'FchServDesde': service_start.strftime(WS_DATE_FORMAT['wsfe']) if service_start else False,
                   'FchServHasta': service_end.strftime(WS_DATE_FORMAT['wsfe']) if service_end else False,
                   'FchVtoPago': due_payment_date.strftime(WS_DATE_FORMAT['wsfe']) if due_payment_date else False,
                   'MonId': self.currency_id.l10n_ar_afip_code,
                   'MonCotiz':  float_repr(self.l10n_ar_currency_rate, precision_digits=6),
                   'CbtesAsoc': ArrayOfCbteAsoc([related_invoices]) if related_invoices else None,
                   'Iva': ArrayOfAlicIva(vat_items) if vat_items else None,
                   'Tributos': ArrayOfTributo(tributes) if tributes else None,
                   'Opcionales': ArrayOfOpcional(optionals) if optionals else None,
                   'Compradores': None}}]}
        return res

    def wsfex_get_cae_request(self, last_id, client):
        if not self.commercial_partner_id.country_id:
            raise UserError(_('For WS "%s" country is required on partner', self.journal_id.l10n_ar_afip_ws))
        elif not self.commercial_partner_id.country_id.code:
            raise UserError(_('For WS "%s" country code is mandatory country: %s', self.journal_id.l10n_ar_afip_ws,
                            self.commercial_partner_id.country_id.name))
        elif not self.commercial_partner_id.country_id.l10n_ar_afip_code:
            hint_msg = afip_errors._hint_msg('country_afip_code', self.journal_id.l10n_ar_afip_ws)
            msg = _('For "%s" WS the afip code country is mandatory: %s', self.journal_id.l10n_ar_afip_ws,
                    self.commercial_partner_id.country_id.name)
            if hint_msg:
                msg += '\n\n' + hint_msg
            raise RedirectWarning(msg, self.env.ref('l10n_ar_edi.action_help_afip').id, _('Go to AFIP page'))

        related_invoices = self._get_related_invoice_data()
        vat_country = 0
        if self.commercial_partner_id.country_id.code != 'AR':
            vat_country = self.commercial_partner_id.country_id.l10n_ar_legal_entity_vat if self.commercial_partner_id.is_company \
                else self.commercial_partner_id.country_id.l10n_ar_natural_vat

        ArrayOfItem = client.get_type('ns0:ArrayOfItem')
        ArrayOfCmp_asoc = client.get_type('ns0:ArrayOfCmp_asoc')

        res = {'Id': last_id,
               'Fecha_cbte': self.invoice_date.strftime(WS_DATE_FORMAT['wsfex']),
               'Cbte_Tipo': self.l10n_latam_document_type_id.code,
               'Punto_vta': self.journal_id.l10n_ar_afip_pos_number,
               'Cbte_nro': self._l10n_ar_get_document_number_parts(
                   self.l10n_latam_document_number, self.l10n_latam_document_type_id.code)['invoice_number'],
               'Tipo_expo': int(self.l10n_ar_afip_concept),
               'permisos': None,
               'Dst_cmp': self.commercial_partner_id.country_id.l10n_ar_afip_code,
               'Cliente': self.commercial_partner_id.name,
               'Domicilio_cliente': " - ".join([
                   self.commercial_partner_id.name or '', self.commercial_partner_id.street or '',
                   self.commercial_partner_id.street2 or '', self.commercial_partner_id.zip or '', self.commercial_partner_id.city or '']),
               'Id_impositivo': self.commercial_partner_id.vat or "",
               'Cuit_pais_cliente': vat_country or 0,
               'Moneda_Id': self.currency_id.l10n_ar_afip_code,
               'Moneda_ctz': float_repr(self.l10n_ar_currency_rate, precision_digits=6),
               'Obs_comerciales': self.invoice_payment_term_id.name if self.invoice_payment_term_id else None,
               'Imp_total': float_repr(self.amount_total, precision_digits=2),
               'Obs': html2plaintext(self.narration),
               'Forma_pago': self.invoice_payment_term_id.name if self.invoice_payment_term_id else None,
               'Idioma_cbte': 1,  # invoice language: spanish / español
               'Incoterms': self.invoice_incoterm_id.code if self.invoice_incoterm_id else None,
               # incoterms_ds only admit max 20 characters admite
               'Incoterms_Ds': self.invoice_incoterm_id.name[:20] if self.invoice_incoterm_id and self.invoice_incoterm_id.name else None,
               # Is required only when afip concept = 1 (Products/Exportation) and if doc code = 19, for all the rest we
               # pass empty string. At the moment we do not have feature to manage permission Id or send 'S'
               'Permiso_existente': "N" if int(self.l10n_latam_document_type_id.code) == 19 and int(self.l10n_ar_afip_concept) == 1 else "",
               'Items': ArrayOfItem(self._get_line_details()),
               'Cmps_asoc': ArrayOfCmp_asoc([related_invoices]) if related_invoices else None}

        # 1671 Report fecha_pago with format YYYMMDD
        # 1672 Is required only doc_type 19. concept (2,4)
        # 1673 If doc_type != 19 should not be reported.
        # 1674 doc_type 19 concept (2,4). date should be >= invoice date
        payment_date = datetime.strftime(self.invoice_date_due, WS_DATE_FORMAT['wsfex']) \
            if int(self.l10n_latam_document_type_id.code) == 19 and int(self.l10n_ar_afip_concept) in [2, 4] and self.invoice_date_due else ''
        if payment_date:
            res.update({'Fecha_pago': payment_date})
        return res

    def wsbfe_get_cae_request(self, last_id, client=None):
        partner_id_code = self._get_partner_code_id(self.commercial_partner_id)
        amounts = self._l10n_ar_get_amounts()
        related_invoices = self._get_related_invoice_data()
        ArrayOfItem = client.get_type('ns0:ArrayOfItem')
        ArrayOfCbteAsoc = client.get_type('ns0:ArrayOfCbteAsoc')
        vat = partner_id_code and self.commercial_partner_id._get_id_number_sanitize()
        res = {'Id': last_id,
               'Tipo_doc': int(partner_id_code) or 0,
               'Nro_doc': vat and int(vat) or 0,
               'Zona': 1,  # National (the only one returned by AFIP)
               'Tipo_cbte': int(self.l10n_latam_document_type_id.code),
               'Punto_vta': int(self.journal_id.l10n_ar_afip_pos_number),
               'Cbte_nro': self._l10n_ar_get_document_number_parts(
                   self.l10n_latam_document_number, self.l10n_latam_document_type_id.code)['invoice_number'],
               'Imp_total': float_round(self.amount_total, precision_digits=2),
               'Imp_tot_conc': float_round(amounts['vat_untaxed_base_amount'], precision_digits=2),  # Not Taxed VAT
               'Imp_neto': float_round(amounts['vat_taxable_amount'], precision_digits=2),
               'Impto_liq': amounts['vat_amount'],
               'Impto_liq_rni': 0.0,  # "no categorizado / responsable no inscripto " figure is not used anymore
               'Imp_op_ex': float_round(amounts['vat_exempt_base_amount'], precision_digits=2),
               'Imp_perc': amounts['vat_perc_amount'] + amounts['profits_perc_amount'] + amounts['other_perc_amount'],
               'Imp_iibb': amounts['iibb_perc_amount'],
               'Imp_perc_mun': amounts['mun_perc_amount'],
               'Imp_internos': amounts['intern_tax_amount'] + amounts['other_taxes_amount'],
               'Imp_moneda_Id': self.currency_id.l10n_ar_afip_code,
               'Imp_moneda_ctz': float_repr(self.l10n_ar_currency_rate, precision_digits=6),
               'Fecha_cbte': self.invoice_date.strftime(WS_DATE_FORMAT['wsbfe']),
               'CbtesAsoc': ArrayOfCbteAsoc([related_invoices]) if related_invoices else None,
               'Items': ArrayOfItem(self._get_line_details())}
        if self.l10n_latam_document_type_id.code in ['201', '206']:  # WS4900
            res.update({'Fecha_vto_pago': self._due_payment_date().strftime(WS_DATE_FORMAT['wsbfe'])})

        optionals = self._get_optionals_data()
        if optionals:
            ArrayOfOpcional = client.get_type('ns0:ArrayOfOpcional')
            res.update({'Opcionales': ArrayOfOpcional(optionals)})
        return res

    def _is_argentina_electronic_invoice(self):
        return bool(self.journal_id.l10n_latam_use_documents and self.env.company.account_fiscal_country_id.code == "AR" and self.journal_id.l10n_ar_afip_ws)

    def _get_last_sequence_from_afip(self):
        """ This method is called to return the highest number for electronic invoices, it will try to connect to AFIP
            only if it is necessary (when we are validating the invoice and need to set the document number)"""
        last_number = 0 if self._is_dummy_afip_validation() or self.l10n_latam_document_number \
            else self.journal_id._l10n_ar_get_afip_last_invoice_number(self.l10n_latam_document_type_id)
        return "%s %05d-%08d" % (self.l10n_latam_document_type_id.doc_code_prefix, self.journal_id.l10n_ar_afip_pos_number, last_number)

    def _get_last_sequence(self, relaxed=False, with_prefix=None):
        """ For argentina electronic invoice, if there is not sequence already then consult the last number from AFIP
        @return: string with the sequence, something like 'FA-A 00001-00000011' """
        res = super()._get_last_sequence(relaxed=relaxed, with_prefix=with_prefix)
        if not res and self._is_argentina_electronic_invoice() and self.l10n_latam_document_type_id:
            res = self._get_last_sequence_from_afip()
        return res
