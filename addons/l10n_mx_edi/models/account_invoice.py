# -*- coding: utf-8 -*-

from odoo import models, fields, api, tools, _

import base64
import ssl
import pytz

from pytz import timezone
from lxml import etree
from datetime import datetime
from suds.client import Client
from itertools import groupby

MX_NS_REFACTORING = {
    'cfdi__': 'cfdi',
}

CERTIFICATE_DATE_FORMAT = '%Y%m%d%H%M%SZ'
ISO_8601_DATE_FORMAT = '%Y-%m-%dT%H:%M:%S'
ERROR_LOG_DATE_FORMAT = '%Y-%m-%d %H:%M:%S'

CFDI_TEMPLATE = 'l10n_mx_edi.mx_invoice'
CFDI_XSD = 'l10n_mx_edi/data/xsd/mx_invoice.xsd'
CFDI_XSLT_CADENA = 'l10n_mx_edi/data/xslt/cadenaoriginal_3_2.xslt'

SUCCESS_SIGN_MSG = _('The sign service has been called with success')
ERROR_SIGN_MSG = _('The sign service requested failed')
SUCCESS_CANCEL_MSG = _('The cancel service has been called with success')
ERROR_CANCEL_MSG = _('The cancel service requested failed')

#---------------------------------------------------------------------------            
# Helpers
#---------------------------------------------------------------------------

def create_list_html(array):
    '''Create a html list of error for the chatter.
    '''
    if not array:
        return ''
    msg = ''
    for item in array:
        msg += '<li>' + item + '</li>'
    return '<ul>' + msg + '</ul>'

def check_with_xsd(cfdi_tree):
    xml_schema_doc = etree.parse(tools.file_open(CFDI_XSD))
    xsd_schema = etree.XMLSchema(xml_schema_doc)
    try:
        xsd_schema.assertValid(cfdi_tree)
        return []
    except etree.DocumentInvalid, xml_errors:
        return [e.message for e in xml_errors.error_log]

class AccountInvoice(models.Model):
    _name = 'account.invoice'
    _inherit = ['account.invoice', 'l10n_mx_edi.pacmixin']

    l10n_mx_edi_sat_status = fields.Selection(
        selection=[
            ('error', 'Error'),
            ('to_sign', 'To sign'),
            ('signed', 'Signed'),
            ('to_cancel', 'To cancel'),
            ('cancelled', 'Cancelled')
        ],
        string='SAT status',
        help='The invoice odoo status must be synchronized with the SAT.',
        readonly=True,
        copy=False,
        stored=True)
    l10n_mx_edi_cfdi_name = fields.Char(
        string='Attachment name',
        help='The attachment must stay reachable after the cancel action.',
        stored=True)

    @api.model
    def l10n_mx_edi_filenames(self):
        '''Get the EDI document name for the Mexican invoicing.
        '''
        self.ensure_one()
        return [self.l10n_mx_edi_cfdi_name] if self.l10n_mx_edi_sat_status == 'signed' else []

    @api.model
    def _l10n_mx_edi_create_cfdi_values(self):
        '''Create the values to fill the CFDI template.
        '''
        precision_digits = self.env['decimal.precision'].precision_get('Account')
        values = {
            'self': self,
            'currency_name': self.currency_id.name,
            'supplier': self.company_id.partner_id.commercial_partner_id,
            'customer': self.partner_id.commercial_partner_id,
            'number': self.number,

            'amount_total': '%0.*f' % (precision_digits, self.amount_total),
            'amount_untaxed': '%0.*f' % (precision_digits, self.amount_untaxed),
            
            # TODO or not TODO: That's the question!
            'pay_method': 'NA',

            'todo': 'TODO'
        }

        values['document_type'] = 'ingreso' if self.type == 'out_invoice' else 'egreso'


        if len(self.payment_term_id.line_ids) > 1:
            values['payment_policy'] = 'Pago en parcialidades'
        else:
            values['payment_policy'] = 'Pago en una sola exhibicion'

        values['domicile'] = '%s %s, %s' % (
                self.company_id.city,
                self.company_id.state_id.name,
                self.company_id.country_id.name
            )

        values['rfc'] = lambda p: p.vat[2:].replace(' ', '')
        values['subtotal_wo_discount'] = lambda l: l.quantity * l.price_unit

        values['total_tax_amount'] = sum([tax.amout for tax in self.tax_line_ids])

        return values

    @api.model
    def l10n_mx_edi_generate(self):
        '''Generate the EDI attachment.
        '''
        self.ensure_one()

        # -----------------------
        # Check the configuration
        # -----------------------

        error_log = []
        values = self._l10n_mx_edi_create_cfdi_values()
        company_id = self.company_id

        # -Check if the certificate is present
        if not company_id.l10n_mx_edi_cer or\
            not company_id.l10n_mx_edi_cer_key or\
            not company_id.l10n_mx_edi_cer_password:
            error_log.append(_('Certificate file/key and/or password is/are missing.'))
        else:
            try:
                pem, certificate = company_id.l10n_mx_edi_load_certificate()
            except Exception as e:
                error_log.append(_('Error loading certificate: %s') % e)

        # -Check if a PAC is specified
        if company_id.l10n_mx_edi_pac:
            pac_test_env = company_id.l10n_mx_edi_pac_test_env
            pac_username = company_id.l10n_mx_edi_pac_username
            pac_password = company_id.l10n_mx_edi_pac_password
            if not pac_test_env and not (pac_username and pac_password):
                error_log.append(_('No PAC credentials specified.'))
        else:
            error_log.append(_('No PAC specified.'))

        # Return pending error_log
        if error_log:
            self.l10n_mx_edi_sat_status = 'error'
            self.message_post(
                body=_('EDI document CFDI failed to be generated:') + create_list_html(error_log),
                subtype='mt_invoice_l10n_mx_edi_msg')
            return []

        # -Check if the certificate is valid
        default_timezone = self._context.get('tz')
        default_timezone = timezone(default_timezone) if default_timezone else pytz.UTC
        mx_timezone = timezone('America/Mexico_City')
        date_invoice_mx = default_timezone.localize(datetime.now())
        # Set date_invoice_mx aware with mexican timezone
        date_invoice_mx = date_invoice_mx.astimezone(mx_timezone)
        # Extract date range from certificate
        before = mx_timezone.localize(
        datetime.strptime(certificate.get_notBefore(), CERTIFICATE_DATE_FORMAT))
        after = mx_timezone.localize(
        datetime.strptime(certificate.get_notAfter(), CERTIFICATE_DATE_FORMAT))
        # Normalize to a more readable format
        if date_invoice_mx < before:
            str_before = before.strftime(ERROR_LOG_DATE_FORMAT)
            error_log.append(_('The certificate is not yet available. (%s)') % str_before)
        if date_invoice_mx > after:
            str_after = after.strftime(ERROR_LOG_DATE_FORMAT)
            error_log.append(_('The certificate is expired. (%s)') % str_after)

        # Break if errors, some fields are missing to generate the EDI document
        if error_log:
            self.l10n_mx_edi_sat_status = 'error'
            self.message_post(
                body=_('EDI document CFDI failed to be generated:') + create_list_html(error_log),
                subtype='mt_invoice_l10n_mx_edi_msg')
            return []

        # -----------------------
        # Create the EDI document
        # -----------------------

        # -Compute date
        values['date'] = date_invoice_mx.strftime(ISO_8601_DATE_FORMAT)

        # -Compute certificate_number
        values['certificate_number'] = ('%x' % certificate.get_serial_number())[1::2]

        # -Compute certificate
        for to_del in ['\n', ssl.PEM_HEADER, ssl.PEM_FOOTER]:
            pem = pem.replace(to_del, '')
        values['certificate'] = pem

        # -Compute cfdi
        # Create unsigned cfdi
        qweb = self.env['ir.qweb']
        content = qweb.render(CFDI_TEMPLATE, values=values)
        # TEMP: refactoring namespaces
        for key, value in MX_NS_REFACTORING.items():
            content = content.replace(key, value + ':')

        # -Compute cadena
        tree = tools.str_as_tree(content)
        xslt_root = etree.parse(tools.file_open(CFDI_XSLT_CADENA))
        cadena = str(etree.XSLT(xslt_root)(tree))
        try:
            cadena_crypted = company_id.l10n_mx_edi_create_encrypted_cadena(cadena)
        except Exception as e:
            self.l10n_mx_edi_sat_status = 'error'
            self.message_post(
                body=_('Failed to generate the cadena:') + create_list_html([str(e)]),
                subtype='mt_invoice_l10n_mx_edi_msg')
            return []
        
        # Post append cadena
        values['cadena'] = cadena_crypted
        tree.attrib['sello'] = cadena_crypted

        # Check with xsd
        error_log = check_with_xsd(tree)
        if error_log:
            self.l10n_mx_edi_sat_status = 'error'
            self.message_post(
                body=_('The generated EDI document is invalid:') + create_list_html(error_log),
                subtype='mt_invoice_l10n_mx_edi_msg')
            return []

        # Post append addenda
        addenda_xml = self.partner_id.l10n_mx_edi_addenda
        addenda_node = tree.find('.//{http://www.sat.gob.mx/cfd/3}Addenda')
        if addenda_xml and addenda_node is not None:
            try:
                addenda_content = qweb.render(addenda_xml.id, values=values)
                addenda_tree = tools.str_as_tree(addenda_content) # filled
                # Multiple addendas under a super node named 'Addenda'
                if len(addenda_tree) == 1 and addenda_tree[0].tag == 'Addenda':
                    addenda_tree = addenda_tree[0]
                addenda_node.extend(addenda_tree)
            except Exception as e:
                error_log.append(str(e))

        # Skip addenda step if some troubles occured
        if error_log:
            self.message_post(
                body=_('Failed to render the cfdi, skip this step:') + create_list_html(error_log),
                subtype='mt_invoice_l10n_mx_edi_msg')

        # Create content
        content = tools.tree_as_str(tree)

        # Create attachment
        filename = '%s-MX-Invoice.xml' % self.number.replace('/', '')
        attachment_id = self.env['ir.attachment'].create({
            'name': filename,
            'res_id': self.id,
            'res_model': unicode(self._name),
            'datas': base64.encodestring(content),
            'datas_fname': filename,
            'type': 'binary',
            'description': 'Mexican invoice',
            })

        # Try to sign the xml
        self.l10n_mx_edi_cfdi_name = filename
        self._l10n_mx_edi_sign()
        return attachment_id

    @api.multi
    def l10n_mx_edi_update_sat_status(self):
        '''Synchronize both systems: Odoo & SAT if the invoices need to be signed or cancelled.
        '''
        for record in self:
            if not record.company_id.l10n_mx_edi_pac:
                continue
            if record.l10n_mx_edi_sat_status == 'to_sign':
                record._l10n_mx_edi_sign()
            elif record.l10n_mx_edi_sat_status == 'to_cancel':
                record._l10n_mx_edi_cancel()

    @api.multi
    def action_invoice_cancel(self):
        result = super(AccountInvoice, self).action_invoice_cancel()
        for record in self:
            country_code = record.company_id.country_id.code
            if country_code == 'MX':
                record._l10n_mx_edi_cancel()
        return result

    #---------------------------------------------------------------------------            
    # PAC related methods
    #---------------------------------------------------------------------------

    @api.multi
    def _l10n_mx_edi_get_cfdi_attachment(self):
        '''Search for the attachment containing the cfdi
        '''
        self.ensure_one()
        name = self.l10n_mx_edi_cfdi_name
        domain = [
            ('res_id','=', self.id),
            ('res_model', '=', self._name),
            ('name', '=', name)]
        return self.env['ir.attachment'].search(domain, limit=1)

    @api.multi
    def _l10n_mx_edi_get_pac_values(self):
        '''Create values that will be used as parameters to request the PAC sign/cancel services.
        '''
        self.ensure_one()
        values = {}
        # Set collapsed cfdi:
        attachment_id = self._l10n_mx_edi_get_cfdi_attachment()
        if attachment_id:
            xml = base64.decodestring(attachment_id.datas)
            tree = tools.str_as_tree(xml)
            node_uuid = tree.find('.//{http://www.sat.gob.mx/TimbreFiscalDigital}TimbreFiscalDigital')
            # not 'if node_uuid': due to the python future tag in this etree version
            if node_uuid is not None:
                values['uuid'] = node_uuid.attrib['UUID']
            values['certificate'] = tree.attrib['certificado']
            xml = tools.tree_as_str(tree, pretty_print=False, xml_declaration=False)
            values['cfdi'] = base64.encodestring(xml)
        return values

    @api.multi
    def _l10n_mx_edi_call_service(self, service_type):
        '''Generic method that contains the logic to call and process a service from the PACs.
        '''
        error_msg = _('Errors while requesting the PAC')
        # Regroup the invoices by company (= by pac)
        comp_x_records = groupby(self, lambda r: r.company_id.id)
        for comp_id, comp_records in comp_x_records:
            # Recreate the record set to call the methods with the right subset
            domain = [
                ('id', 'in', self.ids),
                ('company_id', '=', comp_id)
            ]
            company_id = self.env['res.company'].browse(comp_id)
            records = self.env['account.invoice'].search(domain)
            pac_name = company_id.l10n_mx_edi_pac
            service_func = '_l10n_mx_edi_%s_%s' % (service_type, pac_name)
            # Check if a method is found for this pair service/pac
            if not hasattr(self, service_func):
                for record in records:
                    record.message_post(
                        body=error_msg + create_list_html([_('Methods %s not found') % service_func]), 
                        subtype='mt_invoice_l10n_mx_edi_msg')
                continue
            # Create the client
            client_values = self.l10n_mx_edi_get_pac_client(company_id, service_type)
            error = client_values.pop('error', None)
            client = client_values.pop('client', None)
            username = client_values.pop('username', None)
            password = client_values.pop('password', None)
            multi = client_values.pop('multi', False)
            if error:
                for record in records:
                    record.message_post(
                        body=error_msg + create_list_html([error]), 
                        subtype='mt_invoice_l10n_mx_edi_msg')
                continue
            # If multi is set to true, the method is called with the whole subset.
            # else, we process the service for each record
            if multi:
                records = [records]
            for record in records:
                getattr(record, service_func)(username, password, client)

    @api.multi
    def _l10n_mx_edi_post_sign_process(self, xml_signed, code, msg):
        '''Post process the results of the sign service.
        :xml_signed: the xml signed datas codified in base64
        :code: an eventual error code
        :msg: an eventual error msg
        '''
        self.ensure_one()
        if xml_signed:
            attachment_id = self._l10n_mx_edi_get_cfdi_attachment()
            attachment_name = '%s-MX-Invoice-signed.xml' % self.number.replace('/', '')
            # Store the signed xml in the attachment
            attachment_id.write({
                'name': attachment_name,
                'datas': xml_signed,
                'mimetype': 'application/xml'
            })
            # Update fields values
            self.l10n_mx_edi_sat_status = 'signed'
            self.l10n_mx_edi_cfdi_name = attachment_name
            self.message_post(body=SUCCESS_SIGN_MSG, subtype='mt_invoice_l10n_mx_edi_msg')
        else:
            if msg:
                if code:
                    msg = _('Code %d: %s') % (code, msg)
                msg = create_list_html([msg])
            else:
                msg = ''
            self.message_post(body=ERROR_SIGN_MSG + msg, subtype='mt_invoice_l10n_mx_edi_msg')

    @api.multi
    def _l10n_mx_edi_sign(self):
        '''Call the sign service with records that can be signed.
        '''
        domain = [
            ('l10n_mx_edi_sat_status', 'not in', ['signed', 'to_cancel', 'cancelled', 'error']), 
            ('company_id.l10n_mx_edi_pac', '!=', None),
            ('id', 'in', self.ids)]
        records = self.env['account.invoice'].search(domain)
        records._l10n_mx_edi_call_service('sign')

    @api.multi
    def _l10n_mx_edi_post_cancel_process(self, cancelled, code, msg):
        '''Post process the results of the cancel service.
        :cancelled: is the cancel has been done with success
        :code: an eventual error code
        :msg: an eventual error msg
        '''
        self.ensure_one()
        if cancelled:
            self.l10n_mx_edi_sat_status = 'cancelled'
            self.message_post(body=SUCCESS_CANCEL_MSG, subtype='mt_invoice_l10n_mx_edi_msg')
        else:
            if msg:
                if code:
                    msg = _('Code %d: %s') % (code, msg)
                msg = create_list_html([msg])
            else:
                msg = ''
            self.message_post(body=ERROR_CANCEL_MSG + msg, subtype='mt_invoice_l10n_mx_edi_msg')

    @api.multi
    def _l10n_mx_edi_cancel(self):
        '''Call the cancel service with records that can be signed.
        '''
        record_ids = []
        for record in self:
            # Check SAT status
            if record.l10n_mx_edi_sat_status == 'to_sign':
                record.l10n_mx_edi_sat_status = 'cancelled'
                record.message_post(body=SUCCESS_SERVICE_MSG % 'cancel', subtype='mt_invoice_l10n_mx_edi_msg')
                continue
            if record.l10n_mx_edi_sat_status in ['error', 'cancelled']:
                continue
            record.l10n_mx_edi_sat_status = 'to_cancel'
            if not record.company_id.l10n_mx_edi_pac:
                continue
            record_ids.append(record.id)
        records = self.env['account.invoice'].search([('id', 'in', record_ids)])
        records._l10n_mx_edi_call_service('cancel')

    #---------------------------------------------------------------------------            
    # Solucion Factible PAC
    #---------------------------------------------------------------------------

    @api.multi
    def _l10n_mx_edi_sign_solfact(self, username, password, client):
        '''SIGN for Solucion Factible.
        '''
        # TODO: Do it on multi
        self.ensure_one()
        service = 'timbrar'
        values = self._l10n_mx_edi_get_pac_values()
        params = [username, password, values['cfdi'], False]
        response_values = self.l10n_mx_edi_get_pac_response(service, params, client)
        error = response_values.pop('error', None)
        response = response_values.pop('response', None)
        if error:
            self.message_post(
                body=ERROR_SIGN_MSG + create_list_html([error]), 
                subtype='mt_invoice_l10n_mx_edi_msg')
            return
        code = getattr(response.resultados[0], 'status', None)
        if code:
            code = int(code)
        msg = getattr(response.resultados[0], 'mensaje', None)
        xml_signed = getattr(response.resultados[0], 'cfdiTimbrado', None)
        self._l10n_mx_edi_post_sign_process(xml_signed, code, msg)

    @api.multi
    def _l10n_mx_edi_cancel_solfact(self, username, password, client):
        '''CANCEL for Solucion Factible.
        '''
        # TODO: Do it on multi
        self.ensure_one()
        service = 'cancelar'
        values = self._l10n_mx_edi_get_pac_values()
        uuids = [values['uuid']]
        certificate = self.company_id.l10n_mx_edi_cer
        certificate_key = self.company_id.l10n_mx_edi_cer_key
        certificate_pwd = self.company_id.l10n_mx_edi_cer_password
        params = [username, password, uuids, certificate, certificate_key, certificate_pwd]
        response_values = self.l10n_mx_edi_get_pac_response(service, params, client)
        error = response_values.pop('error', None)
        response = response_values.pop('response', None)
        if error:
            self.message_post(
                body=ERROR_CANCEL_MSG + create_list_html([error]), 
                subtype='mt_invoice_l10n_mx_edi_msg')
            return
        code = getattr(response.resultados[0], 'statusUUID', None)
        if code:
            code = int(code)
        msg = getattr(response.resultados[0], 'mensaje', None)
        cancelled = code == 201 or code == 202
        self._l10n_mx_edi_post_cancel_process(cancelled, code, msg)

    @api.multi
    def _l10n_mx_edi_sign_finkok(self, username, password, client):
        '''SIGN for Finkok.
        '''
        # TODO: Do it on multi
        self.ensure_one()
        service = 'stamp'
        values = self._l10n_mx_edi_get_pac_values()
        params = [[values['cfdi']], username, password]
        response_values = self.l10n_mx_edi_get_pac_response(service, params, client)
        error = response_values.pop('error', None)
        response = response_values.pop('response', None)
        if error:
            self.message_post(
                body=ERROR_SIGN_MSG + create_list_html([error]), 
                subtype='mt_invoice_l10n_mx_edi_msg')
            return
        msg = ''
        code = 0
        if response.Incidencias:
            code = getattr(response.Incidencias[0][0], 'CodigoError', None)
            msg = getattr(response.Incidencias[0][0], 'MensajeIncidencia', None)
        xml_signed = getattr(response, 'xml', None)
        if xml_signed:
            xml_signed = base64.encodestring(xml_signed)
        self._l10n_mx_edi_post_sign_process(xml_signed, code, msg)

    @api.multi
    def _l10n_mx_edi_cancel_finkok(self, username, password, client):
        '''CANCEL for Finkok.
        '''
        # TODO: Do it on multi
        self.ensure_one()
        service = 'cancel'
        values = self._l10n_mx_edi_get_pac_values()
        invoices_list = client.factory.create("UUIDS")
        invoices_list.uuids.string = [values['uuid']]
        company_id = self.company_id
        certificate = company_id.l10n_mx_edi_cer
        certificate_key = company_id.l10n_mx_edi_cer_key
        params = [invoices_list, username, password, certificate, company_id.vat, certificate, certificate_key]
        response_values = self.l10n_mx_edi_get_pac_response(service, params, client)
        error = response_values.pop('error', None)
        response = response_values.pop('response', None)
        if error:
            self.message_post(
                body=ERROR_CANCEL_MSG + create_list_html([error]), 
                subtype='mt_invoice_l10n_mx_edi_msg')
            return
        if not hasattr(response, 'Folios'):
            error = _('A delay of 2 hours has to be respected before to cancel')
            self.message_post(
                body=ERROR_CANCEL_MSG + create_list_html([error]), 
                subtype='mt_invoice_l10n_mx_edi_msg')
            return
        code = getattr(response.Folios[0].Folio, 'EstatusUUID', None)
        cancelled = code == 201 or code == 202  # cancelled or previously cancelled
        msg = code != 201 and code != 202 and "Cancelling get an error"
        self._l10n_mx_edi_post_cancel_process(cancelled, code, msg)