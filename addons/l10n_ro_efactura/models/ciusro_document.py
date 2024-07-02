import io
import requests
import zipfile

from lxml import etree
from odoo import models, fields, api, _
from odoo.exceptions import UserError

NS_UPLOAD = {"ns": "mfp:anaf:dgti:spv:respUploadFisier:v1"}
NS_STATUS = {"ns": "mfp:anaf:dgti:efactura:stareMesajFactura:v1"}
NS_HEADER = {"ns": "mfp:anaf:dgti:efactura:mesajEroriFactuta:v1"}
NS_SIGNATURE = {"ns": "http://www.w3.org/2000/09/xmldsig#"}


class L10nRoEdiDocument(models.Model):
    _name = 'l10n_ro_edi.document'
    _description = "Document object for tracking CIUS-RO XML sent to E-Factura"
    _order = 'datetime DESC, id DESC'

    invoice_id = fields.Many2one(comodel_name='account.move', required=True)
    state = fields.Selection(
        selection=[
            ('invoice_sending', 'Sending'),
            ('invoice_sending_failed', 'Error'),
            ('invoice_sent', 'Sent'),
        ],
        string='E-Factura Status',
        required=True,
    )
    datetime = fields.Datetime(default=fields.Datetime.now, required=True)
    attachment_id = fields.Many2one(comodel_name='ir.attachment')
    message = fields.Char()
    key_loading = fields.Char()
    key_download = fields.Char()
    key_signature = fields.Char()
    key_certificate = fields.Char()
    need_fetch_button = fields.Boolean(compute='_compute_need_fetch_button')

    @api.model
    def _create_document_invoice_sending(self, invoice, key_loading: str):
        self.env['l10n_ro_edi.document'].create({
            'invoice_id': invoice.id,
            'state': 'invoice_sending',
            'key_loading': key_loading,
        })

    @api.model
    def _create_document_invoice_sending_failed(self, invoice, message: str):
        self.env['l10n_ro_edi.document'].create({
            'invoice_id': invoice.id,
            'state': 'invoice_sending_failed',
            'message': message,
        })

    @api.model
    def _create_document_invoice_sent(self, invoice, result: dict):
        document = self.env['l10n_ro_edi.document'].create({
            'invoice_id': invoice.id,
            'state': 'invoice_sent',
            'key_signature': result['key_signature'],
            'key_certificate': result['key_certificate'],
        })
        document.attachment_id = self.env['ir.attachment'].create({
            'name': invoice._l10n_ro_edi_get_attachment_file_name(),
            'raw': result['attachment_raw'],
            'res_model': self._name,
            'res_id': document.id,
            'type': 'binary',
            'mimetype': 'application/xml',
        })

    def unlink(self):
        """ Make sure any created attachments are also deleted """
        self.attachment_id.unlink()
        return super().unlink()

    @api.model
    def _make_efactura_request(self, company, endpoint, method, params, data=None, session=None):
        """ Make an API request to E-Factura and handle the response and return a `result` dictionary
        :param company: `res.company` object containing l10n_ro_edi_access_token
        :param endpoint: 'upload' (for sending) |
                         'stareMesaj' (for fetching status) |
                         'descarcare' (for downloading answer)
        :param method: 'post' (for 'upload') |
                       'get' (for 'stareMesaj'|'descarcare')
        :param params: Dictionary of query parameters
        :param data: xml data for 'upload' request
        :return: dict of {'error': <str>|<bytes>} or {'content': <response.content>} from E-Factura
        """
        url = f"https://api.anaf.ro/test/FCTEL/rest/{endpoint}"
        headers = {'Content-Type': 'application/xml',
                   'Authorization': f'Bearer {company.l10n_ro_edi_access_token}'}

        try:
            requester = session and session or requests
            response = requester.request(method=method, url=url, params=params, data=data, headers=headers, timeout=10)
        except requests.HTTPError as e:
            return {'error': str(e)}
        if response.status_code == 400:
            error_json = response.json()
            return {'error': error_json['message']}
        if response.status_code == 403:
            return {'error': _('Access token is forbidden.')}
        if response.status_code == 204:
            return {'error': _('You reached the limit of requests. Please try again later.')}

        return {'content': response.content}

    @api.model
    def _request_ciusro_send_invoice(self, company, xml_data, move_type='out_invoice'):
        result = self._make_efactura_request(
            company=company,
            endpoint='upload',
            method='POST',
            params={'standard': 'UBL' if move_type == 'out_invoice' else 'CN',
                    'cif': company.vat.replace('RO', '')},
            data=xml_data,
        )
        if 'error' in result:
            return result

        root = etree.fromstring(result['content'])
        res_status = root.get('ExecutionStatus')
        if res_status == '1':
            error_elements = root.findall('.//ns:Errors', namespaces=NS_UPLOAD)
            error_messages = [error_element.get('errorMessage') for error_element in error_elements]
            return {'error': '\n'.join(error_messages)}
        else:
            return {'key_loading': root.get('index_incarcare')}

    @api.model
    def _request_ciusro_fetch_status(self, company, key_loading, session=None):
        result = self._make_efactura_request(
            company=company,
            endpoint='stareMesaj',
            method='GET',
            params={'id_incarcare': key_loading},
            session=session,
        )
        if 'error' in result:
            return result

        root = etree.fromstring(result['content'])
        error_elements = root.findall('.//ns:Errors', namespaces=NS_STATUS)
        if error_elements:
            return {'error': '\n'.join(error_element.get('errorMessage') for error_element in error_elements)}

        state_status = root.get('stare')
        if state_status in ('nok', 'ok'):
            return {'key_download': root.get('id_descarcare')}

    @api.model
    def _request_ciusro_download_answer(self, company, key_download, session=None):
        result = self._make_efactura_request(
            company=company,
            endpoint='descarcare',
            method='GET',
            params={'id': key_download},
            session=session,
        )
        if 'error' in result:
            return result

        # E-Factura gives download response in ZIP format
        zip_ref = zipfile.ZipFile(io.BytesIO(result['content']))
        signature_file = next(file for file in zip_ref.namelist() if 'semnatura' in file)
        xml_bytes = zip_ref.open(signature_file)
        root = etree.parse(xml_bytes)
        error_element = root.find('.//ns:Error', namespaces=NS_HEADER)
        if error_element is not None:
            return {'error': error_element.get('errorMessage')}

        # Pretty-print the XML content of the signature file to be saved as attachment
        attachment_raw = etree.tostring(root, pretty_print=True, xml_declaration=True, encoding='UTF-8')
        return {
            'attachment_raw': attachment_raw,
            'key_signature': root.find('.//ns:SignatureValue', namespaces=NS_SIGNATURE).text,
            'key_certificate': root.find('.//ns:X509Certificate', namespaces=NS_SIGNATURE).text,
        }

    @api.depends('invoice_id.l10n_ro_edi_active_document_id', 'state')
    def _compute_need_fetch_button(self):
        for document in self:
            document.need_fetch_button = (document.invoice_id.l10n_ro_edi_active_document_id.id == document.id and
                                          document.state == 'invoice_sending')

    def action_l10n_ro_edi_fetch_status(self):
        """ Fetch the latest response from E-Factura about the XML sent """
        self.ensure_one()
        if self.state != 'invoice_sending':
            raise UserError(_('This document is not currently in sending state'))
        if not self.key_loading:
            raise UserError(_('This document does not have a loading key'))
        # do the fetch process on a single invoice/document
        self.invoice_id._l10n_ro_edi_fetch_invoice_sending_documents()

    def action_l10n_ro_edi_download_zip(self):
        """ Download the received ZIP file from E-Factura """
        self.ensure_one()
        if not self.attachment_id:
            raise UserError(_('This document does not have any attachment'))
        return {
            'type': 'ir.actions.act_url',
            'url': f'/web/content/{self.attachment_id.id}?download=true',
        }
