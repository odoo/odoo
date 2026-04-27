import io
import zipfile

from base64 import b64encode
from lxml import etree

from odoo import api, fields, models
from odoo.addons.l10n_co_dian import xml_utils


class L10nCoDianDocument(models.Model):
    _inherit = 'l10n_co_dian.document'

    pos_order_id = fields.Many2one(comodel_name='pos.order')

    @api.model
    def _l10n_co_edi_pos_send_to_dian(self, data: dict):
        # ANALOG _send_to_dian in l10n_co_dian
        """ Send an xml to DIAN.
        If the Certification Process is activated, use the dedicated 'SendTestSetAsync' (asynchronous) webservice,
        otherwise, use the 'SendBillSync' (synchronous) webservice.

        :return: a l10n_co_dian.document
        """
        # Zip the xml
        buffer = io.BytesIO()
        with zipfile.ZipFile(buffer, 'w', compression=zipfile.ZIP_DEFLATED) as zipfile_obj:
            zipfile_obj.writestr('invoice.xml', data['xml'])
        zipped_content = buffer.getvalue()

        if data['company_id'].l10n_co_dian_test_environment and data['company_id'].l10n_co_dian_certification_process:
            document_vals = self._l10n_co_edi_pos_send_test_set_async(data={
                'is_sale_document': data['is_sale_document'],
                'company_id': data['company_id'],
                'zipped_content': zipped_content,
            })
        else:
            document_vals = self._l10n_co_edi_pos_send_bill_sync(data={
                'company_id': data['company_id'],
                'zipped_content': zipped_content,
            })

        return self._l10n_co_edi_pos_create_document(
            data={
                'rel_record_data': {
                    'record': data['record'],
                    'field_name': 'pos_order_id',
                },
                'xml': data['xml'],
                'state': document_vals['state'],
                'company_id': data['company_id'],
            },
            **document_vals,
        )

    @api.model
    def _l10n_co_edi_pos_send_bill_sync(self, data: dict):
        # ANALOG _send_bill_sync in l10n_co_dian.l10n_co_dian_document
        """ Send the document to the 'SendBillSync' (synchronous) webservice. """

        if data['company_id'].l10n_co_dian_demo_mode:
            return {
                'state': 'invoice_accepted',
                'message_json': {'status': self.env._("Demo mode response")},
            }

        response = xml_utils._build_and_send_request(
            self,
            payload={
                'file_name': "invoice.zip",
                'content_file': b64encode(data['zipped_content']).decode(),
                'soap_body_template': "l10n_co_dian.send_bill_sync",
            },
            service="SendBillSync",
            company=data['company_id'],
        )

        if not response['response']:
            return {
                'state': 'invoice_sending_failed',
                'message_json': {'status': self.env._("The DIAN server did not respond.")},
            }

        root = etree.fromstring(response['response'])
        if response['status_code'] != 200:
            return {
                'state': 'invoice_sending_failed',
                'message_json': self._build_message(root),
            }

        return {
            'state': 'invoice_accepted' if root.findtext('.//{*}IsValid') == 'true' else 'invoice_rejected',
            'message_json': self._build_message(root),
        }

    @api.model
    def _l10n_co_edi_pos_send_test_set_async(self, data: dict):
        # ANALOG _send_test_set_async in l10n_co_dian
        """ Send the document to the 'SendTestSetAsync' (asynchronous) webservice.
        NB: later, need to fetch the result by calling the 'GetStatusZip' webservice.
        """
        mode = 'invoice' if data['is_sale_document'] else 'bill'
        operation_mode = data['company_id'].l10n_co_dian_operation_mode_ids.filtered(
            lambda operation_mode: operation_mode.dian_software_operation_mode == mode
        )

        response = xml_utils._build_and_send_request(
            self,
            payload={
                'file_name': "invoice.zip",
                'content_file': b64encode(data['zipped_content']).decode(),
                'test_set_id': operation_mode.dian_testing_id,
                'soap_body_template': "l10n_co_dian.send_test_set_async",
            },
            service="SendTestSetAsync",
            company=data['company_id'],
        )

        if not response['response']:
            return {
                'state': 'invoice_sending_failed',
                'message_json': {'status': self.env._("The DIAN server did not respond.")},
            }

        root = etree.fromstring(response['response'])
        if response['status_code'] != 200:
            return {
                'state': 'invoice_sending_failed',
                'message_json': self._build_message(root),
            }

        zip_key = root.findtext('.//{*}ZipKey')
        if zip_key:
            return {
                'state': 'invoice_pending',
                'message_json': {'status': self.env._("Invoice is being processed by the DIAN.")},
                'zip_key': zip_key,
            }

        return {
            'state': 'invoice_rejected',
            'message_json': {'errors': [node.text for node in root.findall('.//{*}ProcessedMessage')]},
        }

    @api.model
    def _l10n_co_edi_pos_create_document(self, data: dict, **kwargs):
        record = data['rel_record_data']['record']
        record.ensure_one()
        root = etree.fromstring(data['xml'])

        # create document
        doc = self.create([{
            data['rel_record_data']['field_name']: record.id,
            'identifier': root.find('.//{*}UUID').text,
            'state': data['state'],
            # naive local colombian datetime
            'datetime': fields.datetime.fromisoformat(root.find('.//{*}SigningTime').text).replace(tzinfo=None),
            'test_environment': data['company_id'].l10n_co_dian_test_environment,
            'certification_process': data['company_id'].l10n_co_dian_certification_process,
            **kwargs,
        }])

        # create attachment
        attachment = self.env['ir.attachment'].create([{
            'raw': data['xml'],
            'name': self.env['pos.edi.xml.ubl_dian']._export_filename(record.l10n_co_edi_pos_name),
            'res_id': doc.id if data['state'] != 'invoice_accepted' else record.id,
            'res_model': doc._name if data['state'] != 'invoice_accepted' else record._name,
        }])

        doc.attachment_id = attachment
        return doc

    def _create_attached_document(self, raw):
        # OVERRIDE l10n_co_dian to take pos_order_id into account
        self.ensure_one()

        if self.move_id:
            prefix = self.move_id._l10n_co_dian_get_attached_document_filename()
        else:
            prefix = self.pos_order_id._l10n_co_edi_pos_get_attached_document_filename()

        return self.env['ir.attachment'].create([{
            'raw': raw,
            'name': f'{prefix}_manual.xml',
            'res_model': 'account.move' if self.move_id else 'pos.order',
            'res_id': (self.move_id or self.pos_order_id).id,
        }])

    def _get_company(self):
        # EXTENDS l10n_co_dian
        self.ensure_one()
        if self.move_id:
            return super()._get_company()

        return self.pos_order_id.company_id

    def _get_identifier_type(self):
        # EXTENDS l10n_co_dian
        self.ensure_one()
        if self.move_id:
            return super()._get_identifier_type()

        return self.pos_order_id._l10n_co_dian_identifier_type()
