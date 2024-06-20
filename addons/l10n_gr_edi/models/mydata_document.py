import requests

from lxml import etree
from odoo import models, fields, api, _
from odoo.tools import cleanup_xml_node


class GreeceEDIDocument(models.Model):
    _name = 'l10n_gr_edi.document'
    _description = "Greece document object for tracking all sent XML to MyDATA"
    _order = 'datetime DESC, id DESC'

    move_id = fields.Many2one(comodel_name='account.move', required=True)
    state = fields.Selection(
        selection=[('move_sent', 'Sent'), ('move_error', 'Error')],
        string='MyDATA Status',
        required=True,
    )
    datetime = fields.Datetime()
    attachment_id = fields.Many2one(comodel_name='ir.attachment', string='XML file')
    message = fields.Char()

    def unlink(self):
        """ Make sure any created attachments are also deleted """
        self.attachment_id.unlink()
        return super().unlink()

    def _get_attachment_file_name(self):
        self.ensure_one()
        return f"{self.move_id.name.replace('/', '_')}_xml_{self.id}.xml"

    @api.model
    def _generate_xml_content(self, xml_vals, send_classification=False):
        xml_template = 'l10n_gr_edi.send_invoice' if not send_classification else \
            'l10n_gr_edi.send_expense_classification'
        xml_content = self.env['ir.qweb']._render(xml_template, xml_vals)
        xml_content = etree.tostring(cleanup_xml_node(xml_content), encoding='ISO-8859-7', standalone='yes')
        xml_content = xml_content.decode('iso8859_7')
        return xml_content

    def _generate_attachments_per_document(self, xml_vals, send_classification=False):
        """ Isolate xml_vals to each individual invoices and generate attachment file for each document """
        for document_index, invoice_vals in enumerate(xml_vals['invoices']):
            single_xml_vals = {'invoices': [invoice_vals]}
            xml_content = self._generate_xml_content(single_xml_vals, send_classification)

            # Generate attachment file per document
            document_id = self[document_index]
            document_id.env['ir.attachment'].create({
                'name': document_id._get_attachment_file_name(),
                'raw': xml_content,
                'mimetype': 'application/xml',
                'res_model': document_id._name,
                'res_id': document_id.id,
                'res_field': 'attachment_id',
            })
            document_id.invalidate_recordset(fnames=['attachment_id'])

    def _request_to_mydata(self, xml_content, send_classification=False):
        """ Make a POST request to MyDATA API """
        endpoint = 'sendexpensesclassification' if send_classification else 'sendinvoices'

        # Record the request time in the datetime field
        self.datetime = fields.Datetime.now()

        try:
            # Send XML to MyDATA API
            response = requests.post(
                url=self.move_id.company_id._l10n_gr_edi_get_mydata_url(endpoint),
                data=xml_content,
                timeout=5,
                headers=self.move_id.company_id._l10n_gr_edi_get_headers_credentials())
        except ConnectionError as err:
            # Handle any connection errors
            self.state = 'move_error'
            self.message = str(err)
            return

        return response

    def _handle_response_xml(self, response):
        """ Handle XML response and update document's state accordingly """
        if not response:
            # In case of status 500 (problem from the server)
            self.state = 'move_error'
            self.message = _('No response from MyDATA, please try again later.')
            return

        root = etree.fromstring(response.content)
        pretty_xml = etree.tostring(root, encoding='unicode', pretty_print=True)
        print(pretty_xml)  # todo remove - monkey testing

        # Handle success/error response per document
        for response_element in root.xpath('//response'):
            response_index = int(response_element.findtext('index'))
            document_id = self[response_index - 1]
            status_code = response_element.findtext('statusCode')

            if status_code == 'Success':
                document_id.state = 'move_sent'
                document_id.message = False
                document_id.move_id.l10n_gr_edi_mark = response_element.findtext('invoiceMark')
                # Delete all previous error documents and keep the latest successfully sent document
                document_id.move_id.l10n_gr_edi_document_ids.filtered(lambda d: d.state != 'move_sent').unlink()
            else:
                document_id.state = 'move_error'
                error_elements = response_element.xpath('./errors/error')
                errors = (f"[{element.findtext('code')}] {element.findtext('message')}." for element in error_elements)
                document_id.message = '\n'.join(errors)

    def _send_mydata_invoices_xml(self, xml_vals):
        """ Send Customer Invoice XML batches to MyDATA. """
        self._generate_attachments_per_document(xml_vals)

        xml_content = self._generate_xml_content(xml_vals)
        print(xml_content)

        response = self._request_to_mydata(xml_content)

        self._handle_response_xml(response)

    def _send_mydata_expense_classifications_xml(self, xml_vals):
        """ Send Vendor Bill Expense Classification XML batches to MyDATA. """
        self._generate_attachments_per_document(xml_vals, send_classification=True)

        xml_content = self._generate_xml_content(xml_vals, send_classification=True)
        print(xml_content)

        response = self._request_to_mydata(xml_content, send_classification=True)

        self._handle_response_xml(response)

    def action_download(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_url',
            'url': f'/web/content/l10n_gr_edi.document/{self.id}/attachment_id/{self._get_attachment_file_name()}?download=true',
        }
