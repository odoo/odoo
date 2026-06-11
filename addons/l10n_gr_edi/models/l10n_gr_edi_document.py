import requests

from lxml import etree
from requests import RequestException

from odoo import api, fields, models, modules
from odoo.tools import cleanup_xml_node


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
        return {'error': str(err)}

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
    _description = "Greece document object for tracking all sent XML to myDATA"
    _order = 'datetime DESC, id DESC'

    move_id = fields.Many2one(comodel_name='account.move', ondelete='cascade')
    picking_id = fields.Many2one(comodel_name='stock.picking', ondelete='cascade')
    state = fields.Selection(
        selection=[
            ('invoice_sent', "Invoice sent"),
            ('invoice_error', "Invoice send failed"),
            ('delivery_note_sent', "Delivery note sent"),
            ('delivery_note_error', "Delivery note send failed"),
            ('bill_fetched', "Expense classification ready to send"),
            ('bill_sent', "Expense classification sent"),
            ('bill_error', "Expense classification send failed"),
        ],
        string='myDATA Status',
        required=True,
        ondelete='cascade',
    )
    datetime = fields.Datetime(default=fields.Datetime.now)
    attachment_id = fields.Many2one(comodel_name='ir.attachment', string='XML File')
    message = fields.Char()

    # Successful document fields
    mydata_mark = fields.Char()
    mydata_cls_mark = fields.Char()
    mydata_url = fields.Char()

    def _l10n_gr_edi_create_error_document(self, record, values: dict):
        """
        Creates ``l10n_gr_edi.document`` of state ``invoice_error`` or ``bill_error`` or ``delivery_note_error``.
        :param values: dictionary in the format of: {'error': <str>, 'xml_content': <optional/str>}
        """
        if record._name == 'account.move':
            state = 'invoice_error' if record.is_sale_document(include_receipts=True) else 'bill_error'
        elif record._name == 'stock.picking':
            state = 'delivery_note_error'

        document = self.create({
            'move_id': record.id if record._name == 'account.move' else None,
            'picking_id': record.id if record._name == 'stock.picking' else None,
            'state': state,
            'message': values['error'],
        })
        if xml_content := values.get('xml_content'):
            document.attachment_id = self.env['ir.attachment'].sudo().create({
                'name': f"mydata_{record.name.replace('/', '_')}.xml",
                'res_model': document._name,
                'res_id': document.id,
                'raw': xml_content,
                'type': 'binary',
                'mimetype': 'application/xml',
            })
        return document

    def _l10n_gr_edi_create_sent_document(self, record, values: dict):
        """
        Creates ``l10n_gr_edi.document`` of state ``invoice_sent``, ``bill_sent`` or ``delivery_note_sent``.
        :param values: dictionary in the format of:
        {
            'mydata_mark': <str>,
            'mydata_cls_mark': <optional/str>,
            'mydata_url': <str>,
            'xml_content': <str>,
        }
        """
        if record._name == 'account.move':
            state = 'invoice_sent' if record.is_sale_document(include_receipts=True) else 'bill_sent'
        elif record._name == 'stock.picking':
            state = 'delivery_note_sent'
        document = self.env['l10n_gr_edi.document'].create({
            'move_id': record.id if record._name == 'account.move' else None,
            'picking_id': record.id if record._name == 'stock.picking' else None,
            'state': state,
            'mydata_mark': values['mydata_mark'],
            'mydata_cls_mark': values.get('mydata_cls_mark'),
            'mydata_url': values['mydata_url'],
        })
        document.attachment_id = self.env['ir.attachment'].sudo().create({
            'name': f"mydata_{record.name.replace('/', '_')}.xml",
            'res_model': record._name,
            'res_id': record.id,
            'raw': values['xml_content'],
            'type': 'binary',
            'mimetype': 'application/xml',
        })
        return document

    @api.model
    def _l10n_gr_edi_handle_send_result(self, record, result, xml_vals):
        """
        Handle the result object received from sending xml to myDATA.
        Create the related error/sent document with the necessary values.
        """
        xml_map = {}  # Dictionary mapping of ``move_id, picking_id`` -> ``xml_content``.
        for vals in xml_vals['invoice_values_list']:
            single_xml_vals = {'invoice_values_list': [vals]}
            move = vals['__move__']
            if record._name == 'account.move' and record.is_purchase_document(include_receipts=True):
                xml_template = 'l10n_gr_edi.mydata_expense_classification'
            else:
                xml_template = 'l10n_gr_edi.mydata_invoice'
            xml_content = self._l10n_gr_edi_generate_xml_content(xml_template, single_xml_vals)
            xml_map[move] = xml_content

        move_ids = list(xml_map.keys())

        if 'error' in result:
            # If the request failed at this stage, it is probably caused by connection/credentials issues.
            # In such case, we don't need to attach the xml here as it won't be helpful for the user.
            for move in move_ids:
                self._l10n_gr_edi_create_error_document(record, result)
        else:
            for result_id, result_dict in result.items():
                move = move_ids[result_id]
                xml_content = xml_map[move]
                document_values = {**result_dict, 'xml_content': xml_content}
                # Delete previous error documents
                move.l10n_gr_edi_document_ids.filtered(lambda d: d.state in ('invoice_error', 'bill_error', 'delivery_note_error')).unlink()
                if 'error' in result_dict:
                    # In this stage, the sending process has succeeded, and any error we receive is generated from the myDATA API.
                    # Previous error(s) without attachments (generated from pre-compute) are now useless and can be unlinked.
                    self._l10n_gr_edi_create_error_document(record, document_values)
                else:
                    self._l10n_gr_edi_create_sent_document(record, document_values)

        if not modules.module.current_test:
            self.env.cr.commit()

    @api.model
    def _l10n_gr_edi_generate_xml_content(self, xml_template, xml_vals):
        xml_content = self.env['ir.qweb']._render(xml_template, xml_vals)
        return etree.tostring(element_or_tree=cleanup_xml_node(xml_content), encoding='ISO-8859-7', standalone='yes')

    def action_download(self):
        """ Download the XML file linked to the document. """
        self.ensure_one()
        return {
            'type': 'ir.actions.act_url',
            'url': f'/web/content/{self.attachment_id.id}?download=true',
        }
