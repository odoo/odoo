# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
import re
import base64
import datetime

from odoo import fields, models, api, _, tools
from odoo.addons.iap import jsonrpc
from odoo.exceptions import UserError
from odoo.tools.safe_eval import safe_eval

DEFAULT_ENDPOINT = 'https://iap-snailmail.odoo.com'
ESTIMATE_ENDPOINT = '/iap/snailmail/1/estimate'
PRINT_ENDPOINT = '/iap/snailmail/1/print'


class SnailmailLetter(models.Model):
    _name = 'snailmail.letter'
    _description = 'Snailmail Letter'

    user_id = fields.Many2one('res.users', 'User sending the letter')
    model = fields.Char('Model', required=True)
    res_id = fields.Integer('Document ID', required=True)
    partner_id = fields.Many2one('res.partner', string='Recipient', required=True)
    company_id = fields.Many2one('res.company', string='Company', required=True, readonly=True,
        default=lambda self: self.env.user.company_id.id)
    report_template = fields.Many2one('ir.actions.report', 'Optional report to print and attach')

    attachment_id = fields.Many2one('ir.attachment', string='Attachment', ondelete='cascade')
    color = fields.Boolean(string='Color', default=lambda self: self.env.user.company_id.snailmail_color)
    duplex = fields.Boolean(string='Both side', default=lambda self: self.env.user.company_id.snailmail_duplex)
    state = fields.Selection([
        ('draft', 'Draft'),
        ('pending', 'In Queue'),
        ('sent', 'Sent'),
        ('error', 'Error'),
        ('canceled', 'Canceled')
        ], 'Status', readonly=True, copy=False, default='draft',
        help="When a letter is created, the status is 'Draft'.\n"
             "If the letter is correctly sent, the status goes in 'Sent',\n"
             "If not, it will got in state 'Error' and the error message will be displayed in the field 'Error Message'.")
    info_msg = fields.Char('Information')

    @api.multi
    def _fetch_attachment(self):
        """
        This method will check if we have any existent attachement matching the model
        and res_ids and create them if not found.
        """
        self.ensure_one()
        obj = self.env[self.model].browse(self.res_id)
        if not self.attachment_id:
            report = self.report_template
            if not report:
                report_name = self.env.context.get('report_name')
                report = self.env['ir.actions.report']._get_report_from_name(report_name)
                if not report:
                    return False
                else:
                    self.write({'report_template': report.id})
                # report = self.env.ref('account.account_invoices')
            if report.print_report_name:
                report_name = safe_eval(report.print_report_name, {'object': obj})
            elif report.attachment:
                report_name = safe_eval(report.attachment, {'object': obj})
            else:
                report_name = 'Document'
            filename = "%s.%s" % (report_name, "pdf")
            pdf_bin, _ = report.with_context(snailmail_layout=True).render_qweb_pdf(self.res_id)
            attachment = self.env['ir.attachment'].create({
                'name': filename,
                'datas': base64.b64encode(pdf_bin),
                'datas_fname': filename,
                'res_model': 'snailmail.letter',
                'res_id': self.id,
                'type': 'binary',  # override default_type from context, possibly meant for another model!
            })
            self.write({'attachment_id': attachment.id})

        return self.attachment_id

    def _count_pages_pdf(self, bin_pdf):
        """ Count the number of pages of the given pdf file.
            :param bin_pdf : binary content of the pdf file
        """
        pages = 0
        for match in re.compile(b"/Count\s+(\d+)").finditer(bin_pdf):
            pages = int(match.group(1))
        return pages

    @api.multi
    def _snailmail_create(self, route):
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
                    city: char,at
                    state: char (state code (OPTIONAL)),
                    country_code: char (country code)
                }
            }],
            options: {
                color: boolean (true if color, false if black-white),
                duplex: boolean (true if duplex, false otherwise),
                currency_name: char
            }
        }
        """
        account_token = self.env['iap.account'].get('snailmail').account_token
        dbuuid = self.env['ir.config_parameter'].sudo().get_param('database.uuid')
        documents = []

        batch = len(self) > 1
        for letter in self:
            document = {
                # generic informations to send
                'letter_id': letter.id,
                'res_model': letter.model,
                'res_id': letter.res_id,
                'contact_address': letter.partner_id.with_context(snailmail_layout=True, show_address=True).name_get()[0][1],
                'address': {
                    'name': letter.partner_id.name,
                    'street': letter.partner_id.street,
                    'street2': letter.partner_id.street2,
                    'zip': letter.partner_id.zip,
                    'state': letter.partner_id.state_id.code if letter.partner_id.state_id else False,
                    'city': letter.partner_id.city,
                    'country_code': letter.partner_id.country_id.code
                },
                'return_address': {
                    'name': letter.company_id.partner_id.name,
                    'street': letter.company_id.partner_id.street,
                    'street2': letter.company_id.partner_id.street2,
                    'zip': letter.company_id.partner_id.zip,
                    'state': letter.company_id.partner_id.state_id.code if letter.company_id.partner_id.state_id else False,
                    'city': letter.company_id.partner_id.city,
                    'country_code': letter.company_id.partner_id.country_id.code,
                }
            }
            # Specific to each case:
            # If we are estimating the price: 1 object = 1 page
            # If we are printing -> attach the pdf
            if route == 'estimate':
                document.update(pages=1)
            else:
                # adding the web logo from the company for future possible customization
                document.update({
                    'company_logo': letter.company_id.logo_web and letter.company_id.logo_web.decode('utf-8') or False,
                })
                attachment = letter._fetch_attachment()
                if attachment:
                    document.update({
                        'pdf_bin': route == 'print' and attachment.datas.decode('utf-8'),
                        'pages': route == 'estimate' and self._count_pages_pdf(base64.b64decode(attachment.datas)),
                    })
                else:
                    letter.write({
                        'info_msg': 'The attachment could not be generated.',
                        'state': 'error',
                        })
                    continue
                if letter.company_id.external_report_layout_id == self.env.ref('l10n_de.external_layout_din5008', False):
                    document.update({
                        'rightaddress': 0,
                    })
            documents.append(document)

        return {
            'account_token': account_token,
            'dbuuid': dbuuid,
            'documents': documents,
            'options': {
                'color': self and self[0].color,
                'duplex': self and self[0].duplex,
                'currency_name': self and self[0].company_id.currency_id.name,
            },
            # this will not raise the InsufficientCreditError which is the behaviour we want for now
            'batch': True,
        }

    def _get_error_message(self, error):
        if error == 'CREDIT_ERROR':
            link = self.env['iap.account'].get_credits_url(service_name='snailmail')
            return _('You don\'t have enough credits to perform this operation.<br>Please go to your <a href=%s target="new">iap account</a>.' % link)
        if error == 'TRIAL_ERROR':
            link = self.env['iap.account'].get_credits_url(service_name='snailmail', trial=True)
            return _('You don\'t have an IAP account registered for this service.<br>Please go to <a href=%s target="new">iap.odoo.com</a> to claim your free credits.' % link)
        if error == 'NO_PRICE_AVAILABLE':
            return _('The country of the partner is not covered by Snailmail.')
        if error == 'MISSING_REQUIRED_FIELDS':
            return _('One or more required fields are empty.')
        if error == 'FORMAT_ERROR':
            return _('The attachment of the letter could not be sent. Please check its content and contact the support if the problem persists.')
        else:
            return _('An unknown error happened. Please contact the support.')
        return error

    @api.multi
    def _snailmail_print(self):
        """
        get response
        {
            'request_code': RESPONSE_OK, # because we receive 200 if good or fail
            'total_cost': total_cost,
            'credit_error': credit_error,
            'request': {
                'documents': documents,
                'options': options
                }
            }
        }
        """
        self.write({'state': 'pending'})
        endpoint = self.env['ir.config_parameter'].sudo().get_param('snailmail.endpoint', DEFAULT_ENDPOINT)
        params = self._snailmail_create('print')
        response = jsonrpc(endpoint + PRINT_ENDPOINT, params=params)
        for doc in response['request']['documents']:
            letter = self.browse(doc['letter_id'])
            record = self.env[doc['res_model']].browse(doc['res_id'])
            if doc.get('sent') and response['request_code'] == 200:
                if hasattr(record, '_message_log'):
                    message = _('The document was correctly sent by post.<br>The tracking id is %s' % doc['send_id'])
                    record._message_log(body=message)
                    letter.write({'info_msg': message, 'state': 'sent'})
            else:
                # look for existing activities related to snailmail to update or create a new one.
                # TODO: in following versions, Add a link to a specifc activity on the letter
                note = _('An error occured when sending the document by post.<br>Error: %s' % \
                    self._get_error_message(doc['error'] if response['request_code'] == 200 else response['reason']))

                domain = [
                    ('summary', 'ilike', '[SNAILMAIL]'),
                    ('res_id', '=', letter.res_id),
                    ('res_model_id', '=', self.env['ir.model']._get(letter.model).id),
                    ('activity_type_id', '=', self.env.ref('mail.mail_activity_data_warning').id),
                ]
                MailActivity = self.env['mail.activity']
                activity = MailActivity.search(domain, limit=1)

                activity_data = {
                    'activity_type_id': self.env.ref('mail.mail_activity_data_warning').id,
                    'summary': '[SNAILMAIL] ' + _('Post letter: an error occured.'),
                    'note': note,
                    'date_deadline': fields.Date.today()
                }
                if activity:
                    activity.update(activity_data)
                else:
                    activity_data.update({
                        'user_id': letter.user_id.id,
                        'res_id': letter.res_id,
                        'res_model_id': self.env['ir.model']._get(letter.model).id,
                    })
                    MailActivity.create(activity_data)

                letter.write({'info_msg': note, 'state': 'error'})

        self.env.cr.commit()

    @api.multi
    def snailmail_print(self):
        self._snailmail_print()

    @api.multi
    def cancel(self):
        self.write({'state': 'canceled'})

    @api.multi
    def _snailmail_estimate(self):
        """
        Return the numbers of stamps needed to send a letter.
        As 1 letter = 1 stamp, we just need to return the number of letters.
        """
        return len(self)

    @api.model
    def _snailmail_cron(self):
        letters_send = self.search([('state', '=', 'pending')])
        if letters_send:
            letters_send._snailmail_print()
        limit_date = datetime.datetime.utcnow() - datetime.timedelta(days=1)
        limit_date_str = datetime.datetime.strftime(limit_date, tools.DEFAULT_SERVER_DATETIME_FORMAT)
        letters_canceled = self.search([
            '|',
                ('state', '=', 'canceled'),
                '&',
                    ('state' ,'=', 'draft'),
                    ('write_date', '<', limit_date_str),
        ])
        letters_canceled.unlink()
