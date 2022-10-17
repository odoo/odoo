# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
import re
import base64
import datetime

from odoo import fields, models, api, _, tools
from odoo.addons.iap import jsonrpc
from odoo.exceptions import UserError, AccessError
from odoo.tools.safe_eval import safe_eval

DEFAULT_ENDPOINT = 'https://iap-snailmail.odoo.com'
PRINT_ENDPOINT = '/iap/snailmail/1/print'
DEFAULT_TIMEOUT = 30

ERROR_CODES = [
    'MISSING_REQUIRED_FIELDS',
    'CREDIT_ERROR',
    'TRIAL_ERROR',
    'NO_PRICE_AVAILABLE',
    'FORMAT_ERROR',
    'UNKNOWN_ERROR',
]


class SnailmailLetter(models.Model):
    _name = 'snailmail.letter'
    _description = 'Snailmail Letter'

    user_id = fields.Many2one('res.users', 'Sent by')
    model = fields.Char('Model', required=True)
    res_id = fields.Integer('Document ID', required=True)
    partner_id = fields.Many2one('res.partner', string='Recipient', required=True)
    company_id = fields.Many2one('res.company', string='Company', required=True, readonly=True,
        default=lambda self: self.env.company.id)
    report_template = fields.Many2one('ir.actions.report', 'Optional report to print and attach')

    attachment_id = fields.Many2one('ir.attachment', string='Attachment', ondelete='cascade')
    attachment_datas = fields.Binary('Document', related='attachment_id.datas')
    attachment_fname = fields.Char('Attachment Filename', related='attachment_id.name')
    color = fields.Boolean(string='Color', default=lambda self: self.env.company.snailmail_color)
    cover = fields.Boolean(string='Cover Page', default=lambda self: self.env.company.snailmail_cover)
    duplex = fields.Boolean(string='Both side', default=lambda self: self.env.company.snailmail_duplex)
    state = fields.Selection([
        ('pending', 'In Queue'),
        ('sent', 'Sent'),
        ('error', 'Error'),
        ('canceled', 'Canceled')
        ], 'Status', readonly=True, copy=False, default='pending', required=True,
        help="When a letter is created, the status is 'Pending'.\n"
             "If the letter is correctly sent, the status goes in 'Sent',\n"
             "If not, it will got in state 'Error' and the error message will be displayed in the field 'Error Message'.")
    error_code = fields.Selection([(err_code, err_code) for err_code in ERROR_CODES], string="Error")
    info_msg = fields.Char('Information')
    display_name = fields.Char('Display Name', compute="_compute_display_name")

    reference = fields.Char(string='Related Record', compute='_compute_reference', readonly=True, store=False)

    message_id = fields.Many2one('mail.message', string="Snailmail Status Message")

    street = fields.Char('Street')
    street2 = fields.Char('Street2')
    zip = fields.Char('Zip')
    city = fields.Char('City')
    state_id = fields.Many2one("res.country.state", string='State')
    country_id = fields.Many2one('res.country', string='Country')

    @api.depends('reference', 'partner_id')
    def _compute_display_name(self):
        for letter in self:
            if letter.attachment_id:
                letter.display_name = "%s - %s" % (letter.attachment_id.name, letter.partner_id.name)
            else:
                letter.display_name = letter.partner_id.name

    @api.depends('model', 'res_id')
    def _compute_reference(self):
        for res in self:
            res.reference = "%s,%s" % (res.model, res.res_id)

    @api.model
    def create(self, vals):
        msg_id = self.env[vals['model']].browse(vals['res_id']).message_post(
            body=_("Letter sent by post with Snailmail"),
            message_type='snailmail'
        )
        partner_id = self.env['res.partner'].browse(vals['partner_id'])
        vals.update({
            'message_id': msg_id.id,
            'street': partner_id.street,
            'street2': partner_id.street2,
            'zip': partner_id.zip,
            'city': partner_id.city,
            'state_id': partner_id.state_id.id,
            'country_id': partner_id.country_id.id,
        })
        return super(SnailmailLetter, self).create(vals)

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
            pdf_bin, _ = report.with_context(snailmail_layout=not self.cover).render_qweb_pdf(self.res_id)
            attachment = self.env['ir.attachment'].create({
                'name': filename,
                'datas': base64.b64encode(pdf_bin),
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
                        'error_code': 'ATTACHMENT_ERROR'
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
                'cover': self and self[0].cover,
                'duplex': self and self[0].duplex,
                'currency_name': 'EUR',
            },
            # this will not raise the InsufficientCreditError which is the behaviour we want for now
            'batch': True,
        }

    def _get_error_message(self, error):
        if error == 'CREDIT_ERROR':
            link = self.env['iap.account'].get_credits_url(service_name='snailmail')
            return _('You don\'t have enough credits to perform this operation.<br>Please go to your <a href=%s target="new">iap account</a>.') % link
        if error == 'TRIAL_ERROR':
            link = self.env['iap.account'].get_credits_url(service_name='snailmail', trial=True)
            return _('You don\'t have an IAP account registered for this service.<br>Please go to <a href=%s target="new">iap.odoo.com</a> to claim your free credits.') % link
        if error == 'NO_PRICE_AVAILABLE':
            return _('The country of the partner is not covered by Snailmail.')
        if error == 'MISSING_REQUIRED_FIELDS':
            return _('One or more required fields are empty.')
        if error == 'FORMAT_ERROR':
            return _('The attachment of the letter could not be sent. Please check its content and contact the support if the problem persists.')
        else:
            return _('An unknown error happened. Please contact the support.')
        return error

    def _snailmail_print(self, immediate=True):
        valid_address_letters = self.filtered(lambda l: l._is_valid_address(l))
        invalid_address_letters = self - valid_address_letters
        invalid_address_letters._snailmail_print_invalid_address()
        if valid_address_letters and immediate:
            for letter in valid_address_letters:
                letter._snailmail_print_valid_address()
                self.env.cr.commit()

    def _snailmail_print_invalid_address(self):
        for letter in self:
            letter.write({
                'state': 'error',
                'error_code': 'MISSING_REQUIRED_FIELDS',
                'info_msg': _('The address of the recipient is not complete')
            })
        self.send_snailmail_update()

    def _snailmail_print_valid_address(self):
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
        endpoint = self.env['ir.config_parameter'].sudo().get_param('snailmail.endpoint', DEFAULT_ENDPOINT)
        timeout = int(self.env['ir.config_parameter'].sudo().get_param('snailmail.timeout', DEFAULT_TIMEOUT))
        params = self._snailmail_create('print')
        try:
            response = jsonrpc(endpoint + PRINT_ENDPOINT, params=params, timeout=timeout)
        except AccessError as ae:
            for doc in params['documents']:
                letter = self.browse(doc['letter_id'])
                letter.state = 'error'
                letter.error_code = 'UNKNOWN_ERROR'
            raise ae
        for doc in response['request']['documents']:
            if doc.get('sent') and response['request_code'] == 200:
                note = _('The document was correctly sent by post.<br>The tracking id is %s' % doc['send_id'])
                letter_data = {'info_msg': note, 'state': 'sent', 'error_code': False}
            else:
                error = doc['error'] if response['request_code'] == 200 else response['reason']

                note = _('An error occured when sending the document by post.<br>Error: %s') % self._get_error_message(error)
                letter_data = {
                    'info_msg': note,
                    'state': 'error',
                    'error_code': error if error in ERROR_CODES else 'UNKNOWN_ERROR'
                }

            letter = self.browse(doc['letter_id'])
            letter.write(letter_data)
        self.send_snailmail_update()

    def send_snailmail_update(self):
        notifications = []
        for letter in self:
            notifications.append([
                (self._cr.dbname, 'res.partner', letter.user_id.partner_id.id),
                {'type': 'snailmail_update', 'elements': letter._format_snailmail_failures()}
            ])
        self.env['bus.bus'].sendmany(notifications)

    def snailmail_print(self):
        self.write({'state': 'pending'})
        if len(self) == 1:
            self._snailmail_print()

    def cancel(self):
        self.write({'state': 'canceled', 'error_code': False})
        self.send_snailmail_update()

    @api.model
    def _snailmail_cron(self, autocommit=True):
        letters_send = self.search([
            '|',
            ('state', '=', 'pending'),
            '&',
            ('state', '=', 'error'),
            ('error_code', 'in', ['TRIAL_ERROR', 'CREDIT_ERROR', 'ATTACHMENT_ERROR', 'MISSING_REQUIRED_FIELDS'])
        ])
        for letter in letters_send:
            letter._snailmail_print()
            if letter.error_code == 'CREDIT_ERROR':
                break  # avoid spam
            # Commit after every letter sent to avoid to send it again in case of a rollback
            if autocommit:
                self.env.cr.commit()

    @api.model
    def fetch_failed_letters(self):
        failed_letters = self.search([('state', '=', 'error'), ('user_id.id', '=', self.env.user.id), ('res_id', '!=', 0), ('model', '!=', False)])
        return failed_letters._format_snailmail_failures()

    @api.model
    def _is_valid_address(self, record):
        record.ensure_one()
        required_keys = ['street', 'city', 'zip', 'country_id']
        return all(record[key] for key in required_keys)

    def _format_snailmail_failures(self):
        """
        A shorter message to notify a failure update
        """
        failures_infos = []
        for letter in self:
            info = {
                'message_id': letter.message_id.id,
                'record_name': letter.message_id.record_name,
                'model_name': self.env['ir.model']._get(letter.model).display_name,
                'uuid': letter.message_id.message_id,
                'res_id': letter.res_id,
                'model': letter.model,
                'last_message_date': letter.message_id.date,
                'module_icon': '/snailmail/static/img/snailmail_failure.png',
                'snailmail_status': letter.error_code if letter.state == 'error' else '',
                'snailmail_error': letter.state == 'error',
                'failure_type': 'snailmail',
            }
            failures_infos.append(info)
        return failures_infos
