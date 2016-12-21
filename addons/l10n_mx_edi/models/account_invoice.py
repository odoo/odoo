# -*- coding: utf-8 -*-

from odoo import models, fields, api, tools, _

import base64
import ssl
import pytz

from pytz import timezone
from lxml import etree
from datetime import datetime
from suds.client import Client

MX_NS_REFACTORING = {
    'cfdi__': 'cfdi',
}

CERTIFICATE_DATE_FORMAT = '%Y%m%d%H%M%SZ'
ISO_8601_DATE_FORMAT = '%Y-%m-%dT%H:%M:%S'
ERROR_LOG_DATE_FORMAT = '%Y-%m-%d %H:%M:%S'

CFDI_TEMPLATE = 'l10n_mx_edi.mx_invoice'
CFDI_XSD = 'l10n_mx_edi/data/xsd/mx_invoice.xsd'
CFDI_XSLT_CADENA = 'l10n_mx_edi/data/xslt/cadenaoriginal_3_2.xslt'

SIGN_SUCCESS_MSG = _('The CFDI document has been successfully signed.')
SIGN_ERROR_MSG = _('The CFDI document failed to be signed.')
CANCEL_SUCCESS_MSG = _('The CFDI document has been successfully cancelled.')
CANCEL_ERROR_MSG = _('The CFDI document failed to be cancelled.')

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
    _inherit = 'account.invoice'

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
    l10n_mx_edi_cancel_date = fields.Datetime(
        string='Cancel Date', 
        help='The datetime of the cancellation', 
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
        addenda_xml = self.partner_id.l10n_mx_edi_addenda.body_xml
        addenda_node = tree.find('.//{http://www.sat.gob.mx/cfd/3}Addenda')
        if addenda_xml and addenda_node is not None:
            try:
                addenda_tree = tools.str_as_tree(addenda_xml) # not filled
                addenda_content = qweb.render(addenda_tree, values=values)
                addenda_tree = tools.str_as_tree(addenda_content) # filled                    
                addenda_node.extend(addenda_tree)
                # No super node found
                if len(addenda_node) == 0:
                    error_log.append(_('No super node found for addenda'))
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
    def _l10n_mx_edi_create_pac_values(self):
        '''Create values that will be used as parameters to request the PAC sign/cancel services.
        '''
        self.ensure_one()
        # Set credentials
        values = {'company_id': self.company_id}
        # Set cancel date
        cancel_date = self.l10n_mx_edi_cancel_date
        if cancel_date:
            default_timezone = self._context.get('tz')
            default_timezone = timezone(default_timezone) if default_timezone else pytz.UTC
            mx_timezone = timezone('America/Mexico_City')
            cancel_date = default_timezone.localize(datetime.now())
            # Set cancel_date aware with mexican timezone
            cancel_date = cancel_date.astimezone(mx_timezone)
            values['cancel_date'] = cancel_date.strftime('%Y-%m-%dT%H:%M:%S')
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
    def _l10n_mx_edi_sign(self):
        '''Call the PAC related to the invoice to create the xml_signed.
        '''
        for record in self:
            pac = record.company_id.l10n_mx_edi_pac
            # Check SAT status
            if record.l10n_mx_edi_sat_status in ['signed', 'to_cancel', 'cancelled', 'error']:
                continue
            record.l10n_mx_edi_sat_status = 'to_sign'
            if not pac:
                continue

            # Call record
            values = record._l10n_mx_edi_create_pac_values()
            sign_func = '_l10n_mx_edi_sign_' + pac
            if not hasattr(record, sign_func):
                return
            try:
                results = getattr(record, sign_func)(values)
            except Exception as e:
               results = {'error': _('Failed to call the suds client: %s' % str(e))}

            # Post process
            error = results.pop('error', None)
            if error:
                record.message_post(
                    body=SIGN_ERROR_MSG + create_list_html([error]), 
                    subtype='mt_invoice_l10n_mx_edi_msg')
                return

            code = results.pop('code', None)
            msg = results.pop('msg', None)
            xml_signed = results.pop('xml_signed', None)
            if xml_signed:
                attachment_id = record._l10n_mx_edi_get_cfdi_attachment()
                attachment_name = '%s-MX-Invoice-signed.xml' % record.number.replace('/', '')
                # Store the signed xml in the attachment
                attachment_id.write({
                    'name': attachment_name,
                    'datas': xml_signed,
                    'mimetype': 'application/xml'
                })
                # Update fields values
                record.l10n_mx_edi_sat_status = 'signed'
                record.l10n_mx_edi_cfdi_name = attachment_name
                record.message_post(body=SIGN_SUCCESS_MSG, subtype='mt_invoice_l10n_mx_edi_msg')
            else:
                if msg:
                    if code:
                        msg = create_list_html([_('Code %d: %s') % (code, msg)])
                else:
                    msg = ''
                record.message_post(
                    body=SIGN_ERROR_MSG + msg, 
                    subtype='mt_invoice_l10n_mx_edi_msg')

    @api.multi
    def _l10n_mx_edi_cancel(self):
        '''Call the PAC related to the record to be cancelled.
        '''
        for record in self:
            pac = record.company_id.l10n_mx_edi_pac
            # Check SAT status
            if record.l10n_mx_edi_sat_status == 'to_sign':
                record.l10n_mx_edi_sat_status = 'cancelled'
                record.message_post(body=CANCEL_SUCCESS_MSG, subtype='mt_invoice_l10n_mx_edi_msg')
                continue
            if record.l10n_mx_edi_sat_status in ['error', 'cancelled']:
                continue
            record.l10n_mx_edi_sat_status = 'to_cancel'
            if not pac:
                continue

            # Call service
            values = record._l10n_mx_edi_create_pac_values()
            cancel_func = '_l10n_mx_edi_cancel_' + pac
            if not hasattr(record, cancel_func):
                return
            try:
                results = getattr(record, cancel_func)(values)
            except Exception as e:
               results = {'error': _('Failed to call the suds client: %s' % str(e))}

            # Post process
            error = results.pop('error', None)
            if error:
                record.message_post(
                    body=CANCEL_ERROR_MSG + create_list_html([error]), 
                    subtype='mt_invoice_l10n_mx_edi_msg')
                return

            code = results.pop('code', None)
            msg = results.pop('msg', None)
            cancelled = results.pop('cancelled', False)
            if cancelled:
                record.l10n_mx_edi_sat_status = 'cancelled'
                record.message_post(body=CANCEL_SUCCESS_MSG, subtype='mt_invoice_l10n_mx_edi_msg')
            else:
                if msg:
                    if code:
                        msg = create_list_html([_('Code %d: %s') % (code, msg)])
                else:
                    msg = ''
                record.message_post(
                    body=CANCEL_ERROR_MSG + msg, 
                    subtype='mt_invoice_l10n_mx_edi_msg')

    #---------------------------------------------------------------------------            
    # Solucion Factible PAC
    #---------------------------------------------------------------------------            

    @api.model
    def _l10n_mx_edi_sign_solfact(self, values):
        self.ensure_one()
        company_id = self.company_id
        if company_id.l10n_mx_edi_pac_test_env:
            url = 'https://testing.solucionfactible.com/ws/services/Timbrado?wsdl'
            username = 'testing@solucionfactible.com'
            password = 'timbrado.SF.16672'
        else:
            url = 'https://solucionfactible.com/ws/services/Timbrado?wsdl'
            username = company_id.l10n_mx_edi_pac_username
            password = company_id.l10n_mx_edi_pac_password
        cfdi = values['cfdi']
        ziped = False

        client = Client(url, timeout=20)
        response = client.service.timbrar(username, password, cfdi, ziped)
        code = getattr(response.resultados[0], 'status', None)
        if code:
            code = int(code)
        msg = getattr(response.resultados[0], 'mensaje', None)
        xml_signed = getattr(response.resultados[0], 'cfdiTimbrado', None)
        return {
            'code': code,
            'msg': msg,
            'xml_signed': xml_signed
        }

    @api.model
    def _l10n_mx_edi_cancel_solfact(self, values):
        self.ensure_one()
        company_id = self.company_id
        if company_id.l10n_mx_edi_pac_test_env:
            url = 'https://testing.solucionfactible.com/ws/services/Timbrado?wsdl'
            username = 'testing@solucionfactible.com'
            password = 'timbrado.SF.16672'
        else:
            url = 'https://solucionfactible.com/ws/services/Timbrado?wsdl'
            username = company_id.l10n_mx_edi_pac_username
            password = company_id.l10n_mx_edi_pac_password

        uuids = [values['uuid']]
        company_id = values['company_id']
        certificate = company_id.l10n_mx_edi_cer
        certificate_key = company_id.l10n_mx_edi_cer_key
        certificate_pwd = company_id.l10n_mx_edi_cer_password

        client = Client(url, timeout=20)
        response = client.service.cancelar(
            username, password, uuids, certificate, certificate_key, certificate_pwd)
        code = getattr(response.resultados[0], 'statusUUID', None)
        if code:
            code = int(code)
        msg = getattr(response.resultados[0], 'mensaje', None)
        cancelled = code == 201 or code == 202 # cancelled or previously cancelled
        return {
            'code': code,
            'msg': msg,
            'cancelled': cancelled
        } 