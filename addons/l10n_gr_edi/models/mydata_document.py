import requests

from lxml import etree
from odoo import models, fields, api, _


def _make_mydata_request(company, endpoint, xml_content) -> dict[str, str] | dict[int, dict[str, str]]:
    """
    Make an API request to myDATA and handle the response and return a `result` dictionary.
    The ``result`` dict keys will always start from 0 and up, corresponding to each move sent.
    It should thus be safe to use them as a list key.

    :param company: `res.company` object containing `l10n_gr_edi_{test_env|aade_id|aade_key}`
    :param endpoint: 'SendInvoices' (for sending invoice) |
                     'SendExpensesClassification' (for sending vendor bill's expense classification) |
                     'RequestDocs' (for fetching third-party-issued invoices (for creating vendor bills))
    :param xml_content: xml content to send to myDATA
    :return: dict[str, str]            error_object    {'error': <str>} |
             dict[int, dict[str, str]] response_object {idx<int>:
                 {'l10n_gr_edi_mark': <str>} | {'l10n_gr_edi_mark': <str>, 'l10n_gr_edi_cls_mark': <str>} | {'error': <str>}
             }
    """
    url = f"https://mydataapidev.aade.gr/{endpoint}" if company.l10n_gr_edi_test_env else \
        f"https://mydatapi.aade.gr/myDATA/{endpoint}"
    print(xml_content)

    try:
        response = requests.post(
            url=url,
            data=xml_content,
            timeout=10,
            headers={'aade-user-id': company.l10n_gr_edi_aade_id,
                     'ocp-apim-subscription-key': company.l10n_gr_edi_aade_key})
    except ConnectionError as err:
        return {'error': str(err)}
    if not response:  # in case of status 429/500 (too many requests / problem from myDATA's server)
        return {'error': _('No response from MyDATA, please try again later. [Status code: %s]', response.status_code)}

    result = {}
    root = etree.fromstring(response.content)
    print(etree.tostring(root, encoding='unicode', pretty_print=True))
    for response_element in root.xpath('//response'):
        response_index = int(response_element.findtext('index')) - 1
        status_code = response_element.findtext('statusCode')
        if status_code == 'Success':
            result[response_index] = {'l10n_gr_edi_mark': str(response_element.findtext('invoiceMark'))}
            if response_cls_mark := response_element.findtext('classificationMark'):  # for in_invoice / in_refund
                result[response_index]['l10n_gr_edi_cls_mark'] = str(response_cls_mark)
        else:
            error_elements = response_element.xpath('./errors/error')
            errors = (f"[{element.findtext('code')}] {element.findtext('message')}." for element in error_elements)
            error_message = '\n'.join(errors)
            result[response_index] = {'error': error_message}

    return result


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
    datetime = fields.Datetime(default=fields.Datetime.now)
    attachment_id = fields.Many2one(comodel_name='ir.attachment', string='XML file')
    message = fields.Char()

    @api.model
    def _mydata_send_invoices(self, company, xml_content):
        return _make_mydata_request(company=company, endpoint='SendInvoices', xml_content=xml_content)

    @api.model
    def _mydata_send_expense_classification(self, company, xml_content):
        return _make_mydata_request(company=company, endpoint='SendExpensesClassification', xml_content=xml_content)

    def action_download(self):
        """ Download the XML file linked to the document. """
        self.ensure_one()
        return {
            'type': 'ir.actions.act_url',
            'url': f'/web/content/{self.attachment_id.id}?download=true',
        }
