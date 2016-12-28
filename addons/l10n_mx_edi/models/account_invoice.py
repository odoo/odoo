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

class AccountInvoice(models.Model):
    _name = 'account.invoice'
    _inherit = ['account.invoice', 'l10n_mx_edi.pacmixin']

    l10n_mx_edi_pac_status = fields.Selection(
        selection=[
            ('retry', 'Retry'),
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
        string='CFDI name',
        help='The attachment name of the CFDI.',
        stored=True)

    #---------------------------------------------------------------------------            
    # PAC related methods
    #---------------------------------------------------------------------------

    @api.multi
    def _l10n_mx_edi_get_pac_values(self):
        '''Create values that will be used as parameters to request the PAC sign/cancel services.
        '''
        self.ensure_one()
        values = {}
        domain = [
            ('res_id','=', self.id),
            ('res_model', '=', self._name),
            ('name', '=', self.l10n_mx_edi_cfdi_name)]
        attachment_id = self.env['ir.attachment'].search(domain, limit=1)
        if attachment_id:
            xml = base64.decodestring(attachment_id.datas)
            tree = tools.str_as_tree(xml)
            node_uuid = tree.find('.//{http://www.sat.gob.mx/TimbreFiscalDigital}TimbreFiscalDigital')
            # not 'if node_uuid': due to the python future tag in this etree version
            if node_uuid is not None:
                values['uuid'] = node_uuid.attrib['UUID']
            cer_domain = [('serial_number', '=', tree.attrib['noCertificado'])]
            values['certificate_id'] = self.env['l10n_mx_edi.certificate'].search(cer_domain, limit=1)
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
        for comp_id, records in comp_x_records:
            company_id = self.env['res.company'].browse(comp_id)
            # Recreate the record set
            records = self.search([('company_id', '=', comp_id), ('id', 'in', self.ids)])
            pac_name = company_id.l10n_mx_edi_pac
            if not pac_name:
                continue
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
            domain = [
                ('res_id','=', self.id),
                ('res_model', '=', self._name),
                ('name', '=', self.l10n_mx_edi_cfdi_name)]
            attachment_id = self.env['ir.attachment'].search(domain, limit=1)
            attachment_id.write({
                'datas': xml_signed,
                'mimetype': 'application/xml' 
            })
            self.l10n_mx_edi_pac_status = 'signed'
            msg = create_list_html([_('The content of the attachment has been updated')])
            self.message_post(body=SUCCESS_SIGN_MSG + msg, subtype='mt_invoice_l10n_mx_edi_msg')
        else:
            if msg:
                if code:
                    code = int(code)
                    msg = _('Code %d: %s') % (code, msg)
                msg = create_list_html([msg])
            else:
                msg = ''
            self.message_post(body=ERROR_SIGN_MSG + msg, subtype='mt_invoice_l10n_mx_edi_msg')

    @api.multi
    def _l10n_mx_edi_sign(self):
        '''Call the sign service with records that can be signed.
        '''
        records = self.search([
            ('l10n_mx_edi_pac_status', 'not in', ['signed', 'to_cancel', 'cancelled', 'retry']),
            ('id', 'in', self.ids)])
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
            self.l10n_mx_edi_pac_status = 'cancelled'
            self.message_post(body=SUCCESS_CANCEL_MSG, subtype='mt_invoice_l10n_mx_edi_msg')
        else:
            if msg:
                if code:
                    code = int(code)
                    msg = _('Code %d: %s') % (code, msg)
                msg = create_list_html([msg])
            else:
                msg = ''
            self.message_post(body=ERROR_CANCEL_MSG + msg, subtype='mt_invoice_l10n_mx_edi_msg')

    @api.multi
    def _l10n_mx_edi_cancel(self):
        '''Call the cancel service with records that can be signed.
        '''
        records = self.search([
            ('l10n_mx_edi_pac_status', 'in', ['to_sign', 'signed', 'to_cancel', 'retry']),
            ('id', 'in', self.ids)])
        for record in records:
            if record.l10n_mx_edi_pac_status in ['to_sign', 'retry']:
                record.l10n_mx_edi_pac_status = 'cancelled'
                record.message_post(body=SUCCESS_SERVICE_MSG % 'cancel', subtype='mt_invoice_l10n_mx_edi_msg')
            else:
                record.l10n_mx_edi_pac_status = 'to_cancel'
        records = self.search([
            ('l10n_mx_edi_pac_status', '=', 'to_cancel'),
            ('id', 'in', self.ids)])
        records._l10n_mx_edi_call_service('cancel')

    #---------------------------------------------------------------------------            
    # PAC service methods
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
        certificate_id = values['certificate_id']
        params = [username, password, uuids, certificate_id.content, certificate_id.key, certificate_id.password]
        response_values = self.l10n_mx_edi_get_pac_response(service, params, client)
        error = response_values.pop('error', None)
        response = response_values.pop('response', None)
        if error:
            self.message_post(
                body=ERROR_CANCEL_MSG + create_list_html([error]), 
                subtype='mt_invoice_l10n_mx_edi_msg')
            return
        code = getattr(response.resultados[0], 'statusUUID', None)
        msg = getattr(response.resultados[0], 'mensaje', None)
        cancelled = code == '201' or code == '202'
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
            xml_signed = xml_signed.encode('ascii', 'xmlcharrefreplace').encode('base64')
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
        certificate_id = values['certificate_id']
        params = [invoices_list, username, password, company_id.vat, certificate_id.content, certificate_id.key]
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
        cancelled = code == '201' or code == '202'  # cancelled or previously cancelled
        msg = code != 201 and code != 202 and "Cancelling get an error"
        self._l10n_mx_edi_post_cancel_process(cancelled, code, msg)

    #---------------------------------------------------------------------------            
    # Account invoice methods
    #---------------------------------------------------------------------------   

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
    def l10n_mx_edi_filenames(self):
        self.ensure_one()
        if not self.l10n_mx_edi_cfdi_name:
            return []
        return [self.l10n_mx_edi_cfdi_name]

    @api.model
    def l10n_mx_edi_generate(self):
        '''Do nothing because the document is generated in an asynchronous way during
        the 'validate' process and by the 'retry' action. 
        '''
        return []

    @api.multi
    def _l10n_mx_edi_create_cfdi(self):
        self.ensure_one()
        qweb = self.env['ir.qweb']
        error_log = []
        company_id = self.company_id
        values = self._l10n_mx_edi_create_cfdi_values()

        # -----------------------
        # Check the configuration
        # -----------------------
        # -Check certificate
        certificate_ids = company_id.l10n_mx_edi_certificate_ids
        certificate_id = certificate_ids.get_valid_certificate()
        if not certificate_id:
            error_log.append(_('No valid certificate found'))

        # -Check PAC
        if company_id.l10n_mx_edi_pac:
            pac_test_env = company_id.l10n_mx_edi_pac_test_env
            pac_username = company_id.l10n_mx_edi_pac_username
            pac_password = company_id.l10n_mx_edi_pac_password
            if not pac_test_env and not (pac_username and pac_password):
                error_log.append(_('No PAC credentials specified.'))
        else:
            error_log.append(_('No PAC specified.'))

        if error_log:
            return {'error': _('Please check your configuration: ') + create_list_html(error_log)}
        
        # -----------------------
        # Create the EDI document
        # -----------------------
        # -Compute certificate data
        values['date'] = certificate_id.get_mx_current_datetime().strftime(ISO_8601_DATE_FORMAT)
        values['certificate_number'] = certificate_id.serial_number
        values['certificate'] = base64.decodestring(certificate_id.data)

        # -Compute cfdi
        cfdi = qweb.render(CFDI_TEMPLATE, values=values)
        # TEMP: refactoring namespaces
        for key, value in MX_NS_REFACTORING.items():
            cfdi = cfdi.replace(key, value + ':')

        # -Compute cadena
        tree = tools.str_as_tree(cfdi)
        xslt_root = etree.parse(tools.file_open(CFDI_XSLT_CADENA))
        cadena = str(etree.XSLT(xslt_root)(tree))
        
        # Post append cadena
        tree.attrib['sello'] = certificate_id.get_encrypted_cadena(cadena)

        # Check with xsd
        error_log = tools.check_with_xsd(tree, CFDI_XSD)
        if error_log:
            return {'error': _('Failed to generate the cadena') + create_list_html(error_log)}

        return {'cfdi': tools.tree_as_str(tree)}

    @api.multi
    def _l10n_mx_edi_retry(self):
        for record in self:
            cfdi_values = record._l10n_mx_edi_create_cfdi()
            error = cfdi_values.pop('error', None)
            cfdi = cfdi_values.pop('cfdi', None)
            if error:
                # cfdi failed to be generated
                record.l10n_mx_edi_pac_status = 'retry'
                record.message_post(body=error, subtype='mt_invoice_l10n_mx_edi_msg')
            else:
                # cfdi has been successfully generated
                record.l10n_mx_edi_pac_status = 'to_sign'
                filename = record.l10n_mx_edi_filenames()[0]
                attachment_id = self.env['ir.attachment'].create({
                    'name': filename,
                    'res_id': record.id,
                    'res_model': unicode(record._name),
                    'datas': base64.encodestring(cfdi),
                    'datas_fname': filename,
                    'type': 'binary',
                    'description': 'Mexican invoice',
                    })
                record.message_post(
                    body=_('CFDI document generated (may be not signed)'),
                    attachment_ids=[attachment_id.id],
                    subtype='account.mt_invoice_edi_created')
                record._l10n_mx_edi_sign()

    @api.multi
    def invoice_validate(self):
        result = super(AccountInvoice, self).invoice_validate()
        for record in self:
            country_code = record.company_id.country_id.code
            if country_code == 'MX':
                record.l10n_mx_edi_cfdi_name = ('%s-MX-Invoice-2.1.xml' % self.number).replace('/', '')
                record._l10n_mx_edi_retry()
        return result

    @api.multi
    def action_invoice_cancel(self):
        result = super(AccountInvoice, self).action_invoice_cancel()
        for record in self:
            country_code = record.company_id.country_id.code
            if country_code == 'MX':
                record._l10n_mx_edi_cancel()
        return result

    @api.multi
    def l10n_mx_edi_update_pac_status(self):
        '''Synchronize both systems: Odoo & PAC if the invoices need to be signed or cancelled.
        '''
        for record in self:
            if record.l10n_mx_edi_pac_status == 'to_sign':
                record._l10n_mx_edi_sign()
            elif record.l10n_mx_edi_pac_status == 'to_cancel':
                record._l10n_mx_edi_cancel()
            elif record.l10n_mx_edi_pac_status == 'retry':
                record._l10n_mx_edi_retry()