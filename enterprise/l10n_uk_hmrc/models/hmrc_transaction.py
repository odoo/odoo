import base64
import hashlib
import re
import requests

from lxml import etree
from xml.etree import ElementTree as ET
from markupsafe import Markup
from urllib.parse import urlparse

from odoo import api, fields, models, _
from odoo.exceptions import RedirectWarning, UserError

TIMEOUT = 10
TEMPLATE_TRANSACTION_ENGINE_REQUEST = "l10n_uk_hmrc.hmrc_transaction_engine_request"
TEMPLATE_TRANSACTION_ENGINE_BASE = "l10n_uk_hmrc.hmrc_transaction_engine_base"
DSP_TEST_ENDPOINT_PREFIX = "https://test-transaction-engine.tax.service.gov.uk"
DSP_PRODUCTION_ENDPOINT_PREFIX = "https://transaction-engine.tax.service.gov.uk"

def _send_request(transaction, xml_document):
        """
        Base method to send a request to HMRC
        IF next_endpoint is NOT SET it will automatically use the default hmrc url: "https://transaction-engine.tax.service.gov.uk/submission" or the test one if in test mode

        :param transaction:     An HMRC transaction
        :param xml_document:    The xml document ready to be sent to hmrc without the header '<?xml version="1.0" encoding="UTF-8"?>'
        :return:                A Tuple containing first the response of the request, and in second another dict containing the header of the response content (See: _get_header_from_response).
        """
        transaction.ensure_one()
        xml_document = Markup('<?xml version="1.0" encoding="UTF-8"?>\n') + xml_document
        if transaction.env['ir.config_parameter'].sudo().get_param("l10n_uk_hmrc.api_mode", 'production') == 'production':
            url_prefix = DSP_PRODUCTION_ENDPOINT_PREFIX
        else:
            url_prefix = DSP_TEST_ENDPOINT_PREFIX
        response = requests.request(
            'POST',
            f"{url_prefix}{transaction.next_endpoint}",
            data=xml_document.encode('utf-8'),
            headers={'content_type': 'text/xml'},
            timeout=TIMEOUT,
        )
        header = transaction._get_header_from_response(response.content)
        return response, header

class HMRCTransaction(models.Model):
    _name = "l10n_uk.hmrc.transaction"
    _description = "Contains a single transaction made to hmrc"
    transaction_type = fields.Selection(
        selection=[('unknown', "Unknown")],
        required=True,
        default='unknown',
    )

    state = fields.Selection(
        string="State",
        selection=[
            ('to_send', "To Send"),
            ('polling', "Polling"),
            ('success', "Success"),
            ('deleted', "Deleted"),
            ('error', "Error"),
        ],
        default='to_send',
    )
    correlation_id = fields.Char(string="Correlation ID")
    next_endpoint = fields.Char(
        string="Next request endpoint",
        default='/submission'
    )
    next_polling = fields.Datetime(string="Next Polling Time")
    completed_datetime = fields.Datetime(string="Completed Time")
    sender_user_id = fields.Many2one(comodel_name='res.users', string="Sender")

    period_start = fields.Date(string="Document period start")
    period_end = fields.Date(string="Document period end")
    company_id = fields.Many2one(comodel_name='res.company', string="Contractor")

    response_attachment_id = fields.Many2one(string="Response Attachment", comodel_name='ir.attachment')

    ##################################################################
    #                   To Override
    ##################################################################
    def _get_transaction_class(self):
        """
        This should be overidden by any transaction engine implementation to provide a class for the document requests
        :return str: the document class
        """
        return None

    ##################################################################
    #                   Requests
    ##################################################################
    

    def _send_delete_request(self, xml_document):
        """
        Send a delete request to HMRC to delete a specific transaction after it has been completed
        This is only called by crons once every month
        See: https://assets.publishing.service.gov.uk/media/5b90f59de5274a0bd7d11954/Transaction.pdf
        """
        self.ensure_one()
        self.next_endpoint = "/submission"
        response, header = _send_request(self, xml_document)

        if header['qualifier'] == 'error':
            error_data = self._get_errors_from_response(response.content)

            if error_data['type'] == 'fatal' and any(error['code'] == 2000 for error in error_data['errors']):
                self.state = 'error'
                return

            self._handle_request_error(error_data, transaction_type='delete')

        else:
            self.state = 'deleted'

    def _send_poll_request(self, xml_document):
        """
        This is the main part of the transaction engine. It is used to poll HMRC when we sent a request to fetch the result or the next time to poll again
        This should not be overriden
        """
        self.ensure_one()
        response, header = _send_request(self, xml_document)
        if header['qualifier'] == 'acknowledgement':
            self.next_endpoint = urlparse(header['response_end_point']).path
            self.state = 'polling'
            self.correlation_id = header['correlation_id']
            self.next_polling = fields.Datetime.add(fields.Datetime.now(), seconds=int(header['poll_interval']))
            return

        self.completed_datetime = fields.Datetime.now()
        tree = etree.fromstring(response.content)
        self.response_attachment_id = self.env['ir.attachment'].create({
            'raw': etree.tostring(tree, pretty_print=True, xml_declaration=True, encoding='UTF-8').decode(),
            'name': f'hmrc_transaction_response_{self.period_end}.xml',
            'res_model': self._name,
            'res_id': self.id,
        })
        if header['qualifier'] == 'error':
            self.state = 'error'
            error_data = self._get_errors_from_response(response.content)
            self._handle_request_error(error_data, 'polling')
        elif header['qualifier'] == 'response':
            self.state = 'success'
            self._handle_success()

    ##################################################################
    #                   Response Handling
    ##################################################################
    def _handle_request_error(self, error_data, transaction_type):
        """
        Handles the request when it resulted with an error after sending it to HMRC Transaction engine.
        Can be overidden.
        Refer to this link for an example (CIS monthly return): https://assets.publishing.service.gov.uk/media/5a7ed5b8e5274a2e87db234c/monthly-return-response-messages.pdf
        """
        if error_data['type'] == 'fatal':
            html_body = Markup("""
                <h4>Fatal: %s</h4>
                <p>%s:%s</p>
            """) % (error_data['code'], error_data['location'], error_data['message'])
            self.company_id.message_post(body=html_body, attachment_ids=self.response_attachment_id.ids)
            return

        errors = Markup().join(
            Markup("<li>{title}:{code} {location}:{message}</li>").format(
                title=_("Code"),
                code=error['code'],
                location=error['location'],
                message=error['message']
            ) for error in error_data['errors']
        )

        error_message = _("Hmrc transaction error") if transaction_type == 'polling' else _("Hmrc transaction deletion error")
        html_body = Markup("""
            <p>%s:</p>
            <ul>%s</ul>
        """) % (error_message, errors)
        self.company_id.message_post(body=html_body, attachment_ids=self.response_attachment_id.ids)

    def _handle_submission_error(self, response, header):
        """
        Handles the errors that might happen when we try to send our xml document.
        These types of errors happens before it is passed to the transaction engine.
        Can be overidden.

        Typically we can receive errors such as wrong user credentials, ...
        Refer to this document: https://assets.publishing.service.gov.uk/media/5b90f59de5274a0bd7d11954/Transaction.pdf
        """
        self.state = 'error'
        error = self._get_errors_from_response(response.content)
        if error['code'] == 1046 or error['code'] == 1002:  # Auth failure
            message = _("The authentication has failed. Please verify your HMRC details on the company.")
            raise RedirectWarning(
                message=message,
                action={
                    'view_mode': 'form',
                    'res_model': 'res.company',
                    'type': 'ir.actions.act_window',
                    'res_id': self.company_id.id,
                    'views': [(False, 'form')],
                },
                button_text=_("Go to company"),
            )
        else:
            message = _("An error happened when sending the document.\n\nDetails:\n%(code)s: %(message)s", code=error['code'], message=error['message'])

        self.company_id.message_post(body=message)
        raise UserError(message)

    def _handle_success(self):
        """
        Called when a transaction resulted in a success for both odoo side and hmrc side.
        Can be overidden.
        """
        html_body = Markup("%s") % _("HMRC Monthly return from %(period_start)s to %(period_end)s succeeded", period_start=self.period_start, period_end=self.period_end)
        self.company_id.message_post(body=html_body, attachment_ids=self.response_attachment_id.ids)

    ##################################################################
    #                   Transaction Crons
    ##################################################################
    @api.model
    def _cron_poll_pending_transactions(self):
        """
        This cron is called once a day. Its purpose is to process all transactions that are in polling state.
        For each of them it checks if we may actually poll them by checking the next_polling time and then send the polling request to HMRC.
        """
        transactions_to_process = self.env['l10n_uk.hmrc.transaction'].search([('state', '=', 'polling')])

        for transaction in transactions_to_process:
            if transaction.next_polling.timestamp() > fields.Datetime.now().timestamp():
                continue

            transaction_data = {
                'correlation_id': transaction.correlation_id,
                'class': transaction._get_transaction_class(),
                'qualifier': 'poll',
                'function': 'submit',
            }
            xml_document = self.env['ir.qweb']._render(TEMPLATE_TRANSACTION_ENGINE_REQUEST, {'transaction': transaction_data})
            transaction._send_poll_request(xml_document)

    @api.model
    def _cron_delete_processed_transactions(self):
        """
        This cron is executed once every month. It acts as a final aknowledgement to HMRC to tell that the sucessful transaction is OK.
        Delete is the way HMRC call this and it is also called here to stay consistent
        """
        transactions_to_delete = self.env['l10n_uk.hmrc.transaction'].search([('state', '=', 'success')])
        for transaction in transactions_to_delete:
            transaction_data = {
                'correlation_id': transaction.correlation_id,
                'class': transaction._get_transaction_class(),
                'qualifier': 'request',
                'function': 'delete',
            }
            xml_document = self.env['ir.qweb']._render(TEMPLATE_TRANSACTION_ENGINE_REQUEST, {'transaction': transaction_data})
            transaction._send_delete_request(xml_document)

    ##################################################################
    #                   XML response utilities
    ##################################################################
    @api.model
    def _get_header_from_response(self, response_xml):
        tree = etree.fromstring(response_xml)
        xpath_namespace = {'x': 'http://www.govtalk.gov.uk/CM/envelope'}
        header_node = tree.xpath("/x:GovTalkMessage/x:Header/x:MessageDetails", namespaces=xpath_namespace)[0]
        return {
            'qualifier': header_node.xpath('./x:Qualifier', namespaces=xpath_namespace)[0].text,
            'correlation_id': header_node.xpath('./x:CorrelationID', namespaces=xpath_namespace)[0].text,
            'response_end_point': header_node.xpath('./x:ResponseEndPoint', namespaces=xpath_namespace)[0].text,
            'poll_interval': header_node.xpath('./x:ResponseEndPoint', namespaces=xpath_namespace)[0].get('PollInterval'),
        }

    @api.model
    def _get_errors_from_response(self, response_xml):
        tree = etree.fromstring(response_xml)
        xpath_namespace = {'x': 'http://www.govtalk.gov.uk/CM/envelope', 'y': 'http://www.govtalk.gov.uk/CM/errorresponse'}
        error_type = tree.xpath("/x:GovTalkMessage/x:GovTalkDetails/x:GovTalkErrors/x:Error/x:Type", namespaces=xpath_namespace)[0].text
        result = {'type': error_type}
        if error_type == 'fatal':
            code = tree.xpath("/x:GovTalkMessage/x:GovTalkDetails/x:GovTalkErrors/x:Error/x:Number", namespaces=xpath_namespace)[0].text
            if code.isdigit():
                code = int(code)
            result['code'] = code
            result['message'] = tree.xpath("/x:GovTalkMessage/x:GovTalkDetails/x:GovTalkErrors/x:Error/x:Text", namespaces=xpath_namespace)[0].text
            result['location'] = tree.xpath("/x:GovTalkMessage/x:GovTalkDetails/x:GovTalkErrors/x:Error/x:Location", namespaces=xpath_namespace)[0].text
            return result

        # business error
        errors_nodes = tree.xpath("/x:GovTalkMessage/x:Body/y:ErrorResponse/y:Error", namespaces=xpath_namespace)
        errors = []
        for error in errors_nodes:
            message_node = error.xpath("./y:Text", namespaces=xpath_namespace)
            location_node = error.xpath("./y:Location", namespaces=xpath_namespace)
            code = error.xpath("./y:Number", namespaces=xpath_namespace)[0].text
            if code.isdigit():
                code = int(code)
            errors.append({
                'code': code,
                'type': error.xpath("./y:Type", namespaces=xpath_namespace)[0].text,
                'message': message_node[0].text if len(message_node) else '',
                'location': location_node[0].text if len(location_node) else '',
            })

        result['errors'] = errors
        return result

    ##################################################################
    #                         Helpers
    ##################################################################

    @api.model
    def _generate_ir_mark(self, data):
        """
        An IRMark must be generated from the body of the message to ensure the integrity to HMRC.
        See: https://www.gov.uk/government/publications/hmrc-irmark-for-gateway-protocol-services
        """
        report_for_ir_mark = self.env['ir.qweb']._render(data['transaction']['body_template'], data)
        report_for_ir_mark = re.sub(r'<IRmark Type="generic">.*<\/IRmark>', '', report_for_ir_mark)
        canonical_xml = ET.canonicalize(report_for_ir_mark)
        # 1.3 "Once the XML is in canonical form a SHA-1 digest must be created from it [...]"
        hashed_result = hashlib.sha1(canonical_xml.encode('utf-8')).digest()
        # 1.4. "The SHA-1 hash can then be Base64 and Base32 encoded. [...]"
        return base64.b64encode(hashed_result).decode('utf-8')

    @api.model
    def _generate_xml_document(self, xml_data):
        return self.env['ir.qweb']._render(TEMPLATE_TRANSACTION_ENGINE_BASE, xml_data)
