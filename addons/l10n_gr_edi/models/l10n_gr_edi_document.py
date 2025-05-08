import requests

from lxml import etree
from requests import RequestException

from odoo import fields, models


def _make_mydata_request(company, endpoint, xml_content) -> dict[str, str] | dict[int, dict[str, str]]:
    """
    Make an API request to myDATA and handle the response and return a `result` dictionary.
    The ``result`` dict keys will always start from 0 and up, corresponding to each move sent.
    It should thus be safe to use them as a list key.

    :param res.company company: `res.company` object containing `l10n_gr_edi_{test_env|aade_id|aade_key}`
    :param str endpoint: 'SendInvoices' (for sending invoice) |
                         'SendExpensesClassification' (for sending vendor bill's expense classification) |
                         'RequestDocs' (for fetching third-party-issued invoices (for creating vendor bills))
    :param str xml_content: xml content to send to myDATA
    :return: dict[str, str]            error_object    {'error': <str>} |
             dict[int, dict[str, str]] response_object {
                 idx<int>:
                     {
                        'mydata_mark': <str>,
                        'mydata_cls_mark': <optional/str>,
                        'mydata_url': <str>,
                     }
                     |
                     { 'error': <str> }
             }
    """
    url = f"https://mydataapidev.aade.gr/{endpoint}" if company.l10n_gr_edi_test_env else \
          f"https://mydatapi.aade.gr/myDATA/{endpoint}"

    try:
        response = requests.post(
            url=url,
            data=xml_content,
            timeout=10,
            headers={
                'aade-user-id': company.l10n_gr_edi_aade_id,
                'ocp-apim-subscription-key': company.l10n_gr_edi_aade_key,
            },
        )
        response.raise_for_status()
        root = etree.fromstring(response.content)
    except (RequestException, ValueError) as err:
        return {'error': err}

    result = {}
    for response_element in root.xpath('//response'):
        response_index = int(response_element.findtext('index') or '1') - 1
        status_code = response_element.findtext('statusCode')
        if status_code == 'Success':
            res_cls_mark = response_element.findtext('classificationMark')
            result[response_index] = {
                'mydata_mark': response_element.findtext('invoiceMark'),
                'mydata_url': response_element.findtext('qrUrl'),
                **({'mydata_cls_mark': res_cls_mark} if res_cls_mark else {}),  # for in_invoice / in_refund
            }
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

    move_id = fields.Many2one(comodel_name='account.move', ondelete='cascade')
    state = fields.Selection(
        selection=[
            ('invoice_sent', "Invoice sent"),
            ('invoice_error', "Invoice send failed"),
            ('bill_fetched', "Expense classification ready to send"),
            ('bill_sent', "Expense classification sent"),
            ('bill_error', "Expense classification send failed"),
        ],
        string='MyDATA Status',
        required=True,
        ondelete='cascade',
    )
    datetime = fields.Datetime(default=fields.Datetime.now)
    attachment_id = fields.Many2one(comodel_name='ir.attachment', string='XML file')
    message = fields.Char()

    # Successful document fields
    mydata_mark = fields.Char()
    mydata_cls_mark = fields.Char()
    mydata_url = fields.Char()

    def action_download(self):
        """ Download the XML file linked to the document. """
        self.ensure_one()
        return {
            'type': 'ir.actions.act_url',
            'url': f'/web/content/{self.attachment_id.id}?download=true',
        }
