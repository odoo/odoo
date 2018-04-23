# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
import re

from odoo import api, fields, models, _
from odoo.addons.iap import jsonrpc

DEFAULT_ENDPOINT = 'https://iap-services.odoo.com'
ESTIMATE_ENDPOINT = '/iap/snailmail/1/estimate'
PRINT_ENDPOINT = '/iap/snailmail/1/print'


class MultiComposer(models.TransientModel):

    _name = 'multi.compose.message'
    _inherit = 'multi.compose.message'

    partner_id = fields.Many2one('res.partner', string='Partner')
    snailmail_color = fields.Boolean(string='Color', default=lambda self: self.env.user.company_id.snailmail_color)
    snailmail_duplex = fields.Boolean(string='Both side', default=lambda self: self.env.user.company_id.snailmail_duplex)
    snailmail_send_by_letter = fields.Boolean('Post', default=lambda self: self.env.user.company_id.snailmail_send_by_letter)

    snailmail_cost = fields.Float(string='Credits', compute='_snailmail_estimate', store=True, readonly=True)
    currency_id = fields.Many2one('res.currency', default=lambda self: self.env.user.company_id.currency_id.id, string="Currency")

    @api.multi
    def _update_company(self):
        super(MultiComposer,self)._update_company()
        for rec in self:
            if rec.company_id.snailmail_send_by_letter != rec.snailmail_send_by_letter:
                rec.company_id.write({
                    'snailmail_send_by_letter': rec.snailmail_send_by_letter,
                })

    @api.multi
    def _snailmail_create(self, route, batch=False):
        """
        Create a dictionnary object to send to snailmail server.

        :return: Dict in the form:
        {
            account_token: string,    //IAP Account token of the user
            documents: [{
                pages: int,
                pdf_bin: pdf file
                res_id: int (client-side res_id),
                res_model: char (client-side res_model),
                address: {
                    name: char,
                    street: char,
                    street2: char (OPTIONAL),
                    zip: int,
                    city: char,
                    state: char (state code (OPTIONAL)),
                    country_code: char (country code)
                }
                return_address: {
                    name: char,
                    street: char,
                    street2: char (OPTIONAL),
                    zip: int,
                    city: char,
                    state: char (state code (OPTIONAL)),
                    country_code: char (country code)
                }
            }],
            options: {
                color: boolean (true if color, false if black-white),
                duplex: boolean (true if duplex, false otherwise),
            }
        }
        """
        account_token = self.env['iap.account'].get('snailmail').account_token
        documents = []
        pdf = self.print_attachment_id.datas
        if pdf:
            documents.append({
                'pdf_bin': route == 'print' and pdf,
                'pages': route == 'estimate' and self._count_pages_pdf(pdf),
                'address': {
                    'name': self.partner_id.name,
                    'street': self.partner_id.street,
                    'street2': self.partner_id.street2,
                    'zip': self.partner_id.zip,
                    'state': self.partner_id.state_id.code if self.partner_id.state_id else False,
                    'city': self.partner_id.city,
                    'country_code': self.partner_id.country_id.code
                },
                'return_address': {
                    'name': self.company_id.partner_id.name,
                    'street': self.company_id.partner_id.street,
                    'street2': self.company_id.partner_id.street2,
                    'zip': self.company_id.partner_id.zip,
                    'state': self.company_id.partner_id.state_id.code if self.company_id.partner_id.state_id else False,
                    'city': self.company_id.partner_id.city,
                    'country_code': self.company_id.partner_id.country_id.code,
                }
            })
        return {
            'account_token': account_token,
            'documents': documents,
            'options': {
                'color': self.snailmail_color,
                'duplex': self.snailmail_duplex,
            },
            'batch': batch,
        }

    @api.multi
    def action_snailmail_print(self):
        """
        get response
        {
            'request_code': RESPONSE_OK, # 200 if good or fail
            'total_cost': total_cost,
            'credit_error': credit_error,
            'request': {
                'documents': documents,
                'options': options
                }
            }
        }
        """
        self.ensure_one()
        endpoint = self.env['ir.config_parameter'].sudo().get_param('snailmail.endpoint', DEFAULT_ENDPOINT)
        params = self._snailmail_create('print', batch=True)
        response = jsonrpc(endpoint + PRINT_ENDPOINT, params=params)

        error = False
        doc = response['request']['documents'][0]
        record = self.env[self.model].browse(self.res_id)
        if doc.get('sent') and response['request_code'] == 200:
            if hasattr(record, '_message_log'):
                message = _('The document was correctly sent by post.<br>The tracking id is %s' % doc['send_id'])
                record._message_log(body=message)
        else:
            activity_data = {
                'res_id': self.res_id,
                'res_model_id': self.env['ir.model']._get(self.model).id,
                'activity_type_id': self.env.ref('snailmail.mail_activity_data_snailmail').id,
                'summary': _('Post letter: an error occured.'),
                'note': _('An error occured when sending the document by post.<br>Error: %s' % \
                self._get_error_message(doc['error'] if response['request_code'] == 200 else response['reason'])),
                'user_id': self.env.user.id,
            }
            self.env['mail.activity'].create(activity_data)
            error = True
        if not error:
            notification = _('Post letter: document sent.')
        else:
            notification = _('Post letter: an error occured. Please check the document for more information.')
        # as we interact with the exterior world, we commit
        self.env.cr.commit()
        self._update_company()
        return {
            'error': error,
            'message': notification,
        }

    @api.multi
    @api.depends('print_attachment_id')
    @api.onchange('snailmail_send_by_letter')
    def _snailmail_estimate(self):
        """
        Send a request to estimate the cost of sending all the documents with
        the differents options.

        The JSON object sent is the one generated from self._snailmail_create()

        arguments sent:
        {
            "documents":[{
                pages: int,
                res_id: int (client_side, optional),
                res_model: int (client_side, optional),
                address: {
                    country_code: char (country name)
                }
            }],
            'color': # color on the letter,
            'duplex': # one/two side printing,
        }

        The answer of the server is the same JSON object with some additionnal fields:
        {
            "total_cost": integer,      //The cost of sending ALL the documents
            body: JSON object (same as body param except new param 'cost' in each documents)
        }
        """
        for composer in self:
            if not composer.partner_id:
                composer.partner_id = self.env[self.model].browse(self.res_id).partner_id

            if composer.snailmail_send_by_letter and composer.print_attachment_id :# and not composer.is_estimated:
                endpoint = self.env['ir.config_parameter'].sudo().get_param('snailmail.endpoint', DEFAULT_ENDPOINT)

                params = composer._snailmail_create('estimate')
                req = jsonrpc(endpoint + '/iap/snailmail/1/estimate', params=params)
                composer.is_estimated = True

                # The cost is sent in eurocents, we change it to euros and then convert it to the company currency
                cost = int(req['total_cost'])/100.0
                currency_eur = self.env.ref('base.EUR')

                composer.snailmail_cost = currency_eur._convert(cost, self.currency_id, self.company_id, fields.Datetime.now())

    # all the print stuff will go to the cron onsnailail print orders

    def _count_pages_pdf(self, bin_pdf):
        """ Count the number of pages of the given pdf file.
            :param bin_pdf : binary content of the pdf file
        """
        pages = 0
        for match in re.compile(b"/Count\s+(\d+)").finditer(bin_pdf):
            pages = int(match.group(1))
        return pages

    def _get_error_message(self, error):
        if error == 'CREDIT_ERROR':
            link = self.env['iap.account'].get_credits_url(service_name='snailmail')
            return _('You don\'t have enough credits to perform this operation.<br>Please go to your <a href=%s target="new">iap account</a>.' % link)
        if error == 'NO_PRICE_AVAILABLE':
            return _('The country of the partner is not covered by Snailmail.')
        if error == 'MISSING_REQUIRED_FIELDS':
            return _('One or more required fields are empty.')
        if error == 'SOMETHING_IS_WRONG':
            return _('An unknown error happened. Please contact the support.')
        return error


    @api.multi
    def send_and_print_action(self):
        res = super(MultiComposer,self).send_and_print_action()
        if self.snailmail_send_by_letter:
            self.action_snailmail_print()
        return res

    @api.multi
    def send_action(self):
        res = super(MultiComposer,self).send_action()
        for wizard in self:
            if wizard.snailmail_send_by_letter:
                wizard.action_snailmail_print()
        return res
