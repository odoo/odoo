# coding: utf-8

from odoo import _
from odoo.tools import html_escape
import re

import base64
import logging
import zipfile
import io
import socket
import requests
from lxml import etree

from datetime import datetime
from hashlib import sha256

from odoo.tools.zeep import Client, Plugin
from odoo.tools.zeep.exceptions import Fault
from odoo.tools.zeep.wsse.username import UsernameToken


_logger = logging.getLogger(__name__)
# uncomment to enable logging of Zeep requests and responses
# logging.getLogger('zeep.transports').setLevel(logging.DEBUG)


class CarvajalPlugin(Plugin):

    def egress(self, envelope, http_headers, operation, binding_options):
        self.log(envelope, 'carvajal_request')
        return envelope, http_headers

    def ingress(self, envelope, http_headers, operation):
        self.log(envelope, 'carvajal_response')
        return envelope, http_headers

    def log(self, xml, func):
        _logger.debug('%s with\n%s' % (func, etree.tostring(xml, encoding='utf-8', xml_declaration=True, pretty_print=True)))


class CarvajalUsernameToken(UsernameToken):
    def _create_password_digest(self):
        """Carvajal expects a password hashed with sha256 with the
        PasswordText type, together with a Nonce and Created
        element. To do so we can manually specify a password_digest
        (instead of password) to avoid the standard sha1 hashing and
        we can set use_digest=True to add the Nonce and Created. The
        only problem with this approach is that the password will have
        the PasswordDigest type, which Carvajal doesn't accept for
        some reason. This replaces it with PasswordText, which is
        commonly used for non-sha1 hashed passwords.
        """
        res = super(CarvajalUsernameToken, self)._create_password_digest()
        res[0].attrib['Type'] = res[0].attrib['Type'].replace('PasswordDigest', 'PasswordText')
        return res


class CarvajalRequest():
    def __init__(self, move_type, company):
        l10n_co_edi_account = company.sudo().l10n_co_edi_account or ''
        if move_type in ('in_refund', 'in_invoice') and len(l10n_co_edi_account.split('_')) == 2:
            l10n_co_edi_account = l10n_co_edi_account.split('_')[0] + "_DS" + l10n_co_edi_account.split('_')[1]
        self.username = company.sudo().l10n_co_edi_username or ''
        self.password = company.sudo().l10n_co_edi_password or ''
        self.co_id_company = company.l10n_co_edi_company or ''
        self.account = l10n_co_edi_account
        self.test_mode = company.l10n_co_edi_test_mode
        self.wsdl = 'https://wscenf%s.cen.biz/isows/InvoiceService?wsdl' % ('lab' if self.test_mode else '')

    @property
    def client(self):
        if not hasattr(self, '_client'):
            token = self._create_wsse_header(self.username, self.password)
            self._client = Client(self.wsdl, plugins=[CarvajalPlugin()], wsse=token, operation_timeout=10)
        return self._client

    def _handle_exception(self, e):
        '''Handles an exception from Carvajal

        :returns:     A dictionary.
        * error:       The message of the error.
        * blocking_level: Info, warning, error.
        '''
        _logger.error(e)
        if isinstance(e, socket.timeout):
            return {'error': _('Connection to Carvajal timed out.'), 'blocking_level': 'warning'}
        elif isinstance(e, requests.HTTPError) and 499 < e.response.status_code < 600:
            return {'error': _('Carvajal service not available.'), 'blocking_level': 'warning'}
        elif isinstance(e, Fault):
            return {'error': e.message}
        else:
            return {'error': ('Electronic invoice submission to Carvajal failed.'), 'blocking_level': 'warning'}

    def _create_wsse_header(self, username, password):
        created = datetime.now()
        token = CarvajalUsernameToken(username=username, password_digest=sha256(password.encode()).hexdigest(), use_digest=True, created=created)

        return token

    def upload(self, filename, xml):
        '''Upload an XML to carvajal.

        :returns:         A dictionary.
        * message:        Message from carvajal.
        * transactionId:  The Carvajal ID of this request.
        * error:          An eventual error.
        * blocking_level: Info, warning, error.
        '''
        try:
            response = self.client.service.Upload(fileName=filename, fileData=base64.b64encode(xml).decode(),
                                                  companyId=self.co_id_company, accountId=self.account)
        except Exception as e:
            return self._handle_exception(e)

        return {
            'message': html_escape(response.status),
            'transactionId': response.transactionId,
        }

    def _download(self, invoice):
        '''Downloads a ZIP containing an official XML and signed PDF
        document. This will only be available for invoices that have
        been successfully validated by Carvajal and the government.

        Method called by the user to download the response from the
        processing of the invoice by the DIAN and also get the CUFE
        signature out of that file.

        :returns:                    A dictionary.
        * file_name:                 The name of the signed XML.
        * content:                   The content of the signed XML.
        * attachments:               The documents (xml and pdf) received by Carvajal.
        * l10n_co_edi_cufe_cude_ref: The CUFE unique ID of the signed XML.
        * error:                     An eventual error.
        * blocking_level:            Info, warning, error.
        '''
        carvajal_type = False
        if invoice.move_type == 'out_refund':
            carvajal_type = 'NC'
        elif invoice.move_type == 'out_invoice':
            if invoice.journal_id.l10n_co_edi_debit_note or invoice.l10n_co_edi_operation_type in ['30', '32', '33']:
                carvajal_type = 'ND'
            else:
                odoo_type_to_carvajal_type = {
                    '1': 'FV',
                    '2': 'FE',
                    '3': 'FC',
                    '4': 'FC',
                }
                carvajal_type = odoo_type_to_carvajal_type[invoice.l10n_co_edi_type]
        elif invoice.move_type == 'in_invoice':
            carvajal_type = 'DS'
        elif invoice.move_type == 'in_refund':
            carvajal_type = 'NS'

        prefix = invoice.sequence_prefix
        if invoice.move_type == 'out_invoice' and invoice.journal_id.l10n_co_edi_debit_note:
            prefix = 'ND'

        try:
            response = self.client.service.Download(documentPrefix=prefix, documentNumber=invoice.name,
                                                    documentType=carvajal_type, resourceType='PDF,SIGNED_XML',
                                                    companyId=self.co_id_company, accountId=self.account)
        except Exception as e:
            return self._handle_exception(e)
        else:
            filename = re.sub(r'[^\w\s-]', '', invoice.name.lower())
            filename = '%s.zip' % re.sub(r'[-\s]+', '-', filename).strip('-_')
            data = base64.b64decode(response.downloadData)
            zip_ref = zipfile.ZipFile(io.BytesIO(data))
            xml_filenames = [f for f in zip_ref.namelist() if f.endswith('.xml')]
            if xml_filenames:
                xml_file = zip_ref.read(xml_filenames[0])
                content = etree.fromstring(xml_file)
                ref_elem = content.find(".//{*}UUID")
                return {
                    'filename': xml_filenames[0],
                    'xml_file': xml_file,
                    'attachments': [(filename, data)],
                    'message': _('The invoice was succesfully signed. <br/>Message from Carvajal: %s', html_escape(response['status'])),
                    'l10n_co_edi_cufe_cude_ref': ref_elem.text,
                }
            return {'error': _('The invoice was accepted by Carvajal but unexpected response was received.'), 'blocking_level': 'warning'}

    def check_status(self, invoice):
        '''Checks the status of an already sent invoice, and if the invoice has been accepted,
        downloads the signed invoice.

        :returns:                    A dictionary.
        * file_name:                 The name of the signed XML.
        * content:                   The content of the signed XML.
        * attachments:               The documents (xml and pdf) received by Carvajal.
        * l10n_co_edi_cufe_cude_ref: The CUFE unique ID of the signed XML.
        * message:                   The message from the government
        * error:                     An eventual error.
        * blocking_level:            Info, warning, error.
        '''
        try:
            response = self.client.service.DocumentStatus(transactionId=invoice.l10n_co_edi_transaction,
                                                          companyId=self.co_id_company, accountId=self.account)
        except Exception as e:
            return self._handle_exception(e)

        processStatus = response.processStatus if hasattr(response, 'processStatus') else None
        processName = response.processName if hasattr(response, 'processName') else None
        legalStatus = response.legalStatus if hasattr(response, 'legalStatus') else None

        if processStatus == 'OK' and \
                processName in ('PDF_CREATION', 'ISSUANCE_CHECK_DELIVERY', 'SEND_TO_RECEIVER', 'SEND_TO_SENDER', 'SEND_NOTIFICATION') and \
                legalStatus == 'ACCEPTED':
            return self._download(invoice)
        elif processStatus == 'PROCESSING' or \
                (processStatus == 'OK' and legalStatus != 'REJECTED') or (processStatus == 'FAIL' and legalStatus == 'RETRY'):
            return {'error': _('The invoice is still processing by Carvajal.'), 'blocking_level': 'info'}
        else:  # legalStatus == 'REJECTED' or (processStatus == 'FAIL' and legalStatus != 'RETRY')
            if hasattr(response, 'errorMessage') and response['errorMessage']:
                errorMsg = ('Validation error from DIAN. Please refer to the Carvajal Platform for more details.'
                            if response['errorMessage'] == 'DIAN_RESULT'
                            else html_escape(response['errorMessage']).replace('\n', '<br/>'))
                msg = _('The invoice was rejected by Carvajal: %s', errorMsg)
            else:
                msg = _('The invoice was rejected by Carvajal but no error message was received.')
            return {'error': msg, 'blocking_level': 'error'}
