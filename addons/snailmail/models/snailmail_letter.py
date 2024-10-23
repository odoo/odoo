# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
import re
import base64
import io

from reportlab.platypus import Frame, Paragraph, KeepInFrame
from reportlab.lib.units import mm
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.pdfgen.canvas import Canvas

from odoo import fields, models, api, _
from odoo.addons.iap.tools import iap_tools
from odoo.exceptions import AccessError, UserError
from odoo.tools.pdf import PdfFileReader, PdfFileWriter
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
    'ATTACHMENT_ERROR',
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

    attachment_id = fields.Many2one('ir.attachment', string='Attachment', ondelete='cascade', index='btree_not_null')
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

    reference = fields.Char(string='Related Record', compute='_compute_reference', readonly=True, store=False)

    message_id = fields.Many2one('mail.message', string="Snailmail Status Message", index='btree_not_null')
    notification_ids = fields.One2many('mail.notification', 'letter_id', "Notifications")

    street = fields.Char('Street')
    street2 = fields.Char('Street2')
    zip = fields.Char('Zip')
    city = fields.Char('City')
    state_id = fields.Many2one("res.country.state", string='State')
    country_id = fields.Many2one('res.country', string='Country')

    @api.depends('attachment_id', 'partner_id')
    def _compute_display_name(self):
        for letter in self:
            if letter.attachment_id:
                letter.display_name = f"{letter.attachment_id.name} - {letter.partner_id.name}"
            else:
                letter.display_name = letter.partner_id.name

    @api.depends('model', 'res_id')
    def _compute_reference(self):
        for res in self:
            res.reference = "%s,%s" % (res.model, res.res_id)

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            msg_id = self.env[vals['model']].browse(vals['res_id']).message_post(
                body=_("Letter sent by post with Snailmail"),
                message_type='snailmail',
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
        letters = super().create(vals_list)

        notification_vals = []
        for letter in letters:
            notification_vals.append({
                'author_id': letter.message_id.author_id.id,
                'mail_message_id': letter.message_id.id,
                'res_partner_id': letter.partner_id.id,
                'notification_type': 'snail',
                'letter_id': letter.id,
                'is_read': True,  # discard Inbox notification
                'notification_status': 'ready',
            })

        self.env['mail.notification'].sudo().create(notification_vals)

        letters.attachment_id.check('read')
        return letters

    def write(self, vals):
        res = super().write(vals)
        if 'attachment_id' in vals:
            self.attachment_id.check('read')
        return res

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
            if report.print_report_name:
                report_name = safe_eval(report.print_report_name, {'object': obj})
            elif report.attachment:
                report_name = safe_eval(report.attachment, {'object': obj})
            else:
                report_name = 'Document'
            filename = "%s.%s" % (report_name, "pdf")
            paperformat = report.get_paperformat()
            if (paperformat.format == 'custom' and paperformat.page_width != 210 and paperformat.page_height != 297) or paperformat.format != 'A4':
                raise UserError(_("Please use an A4 Paper format."))
            pdf_bin, unused_filetype = self.env['ir.actions.report'].with_context(snailmail_layout=not self.cover, lang='en_US')._render_qweb_pdf(report, self.res_id)
            pdf_bin = self._overwrite_margins(pdf_bin)
            if self.cover:
                pdf_bin = self._append_cover_page(pdf_bin)
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
        for match in re.compile(rb"/Count\s+(\d+)").finditer(bin_pdf):
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
            recipient_name = letter.partner_id.name or letter.partner_id.parent_id and letter.partner_id.parent_id.name
            if not recipient_name:
                letter.write({
                    'info_msg': _('Invalid recipient name.'),
                    'state': 'error',
                    'error_code': 'MISSING_REQUIRED_FIELDS'
                    })
                continue
            document = {
                # generic informations to send
                'letter_id': letter.id,
                'res_model': letter.model,
                'res_id': letter.res_id,
                'contact_address': letter.partner_id.with_context(snailmail_layout=True, show_address=True).display_name,
                'address': {
                    'name': recipient_name,
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
            return _('You don\'t have enough credits to perform this operation.<br>Please go to your <a href=%s target="new">iap account</a>.', link)
        if error == 'TRIAL_ERROR':
            link = self.env['iap.account'].get_credits_url(service_name='snailmail', trial=True)
            return _('You don\'t have an IAP account registered for this service.<br>Please go to <a href=%s target="new">iap.odoo.com</a> to claim your free credits.', link)
        if error == 'NO_PRICE_AVAILABLE':
            return _('The country of the partner is not covered by Snailmail.')
        if error == 'MISSING_REQUIRED_FIELDS':
            return _('One or more required fields are empty.')
        if error == 'FORMAT_ERROR':
            return _('The attachment of the letter could not be sent. Please check its content and contact the support if the problem persists.')
        else:
            return _('An unknown error happened. Please contact the support.')
        return error

    def _get_failure_type(self, error):
        if error == 'CREDIT_ERROR':
            return 'sn_credit'
        if error == 'TRIAL_ERROR':
            return 'sn_trial'
        if error == 'NO_PRICE_AVAILABLE':
            return 'sn_price'
        if error == 'MISSING_REQUIRED_FIELDS':
            return 'sn_fields'
        if error == 'FORMAT_ERROR':
            return 'sn_format'
        else:
            return 'sn_error'

    def _snailmail_print(self, immediate=True):
        valid_address_letters = self.filtered(lambda l: l._is_valid_address(l))
        invalid_address_letters = self - valid_address_letters
        invalid_address_letters._snailmail_print_invalid_address()
        if valid_address_letters and immediate:
            for letter in valid_address_letters:
                letter._snailmail_print_valid_address()
                self.env.cr.commit()

    def _snailmail_print_invalid_address(self):
        error = 'MISSING_REQUIRED_FIELDS'
        error_message = _("The address of the recipient is not complete")
        self.write({
            'state': 'error',
            'error_code': error,
            'info_msg': error_message,
        })
        self.notification_ids.sudo().write({
            'notification_status': 'exception',
            'failure_type': self._get_failure_type(error),
            'failure_reason': error_message,
        })
        self.message_id._notify_message_notification_update()

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
            response = iap_tools.iap_jsonrpc(endpoint + PRINT_ENDPOINT, params=params, timeout=timeout)
        except AccessError as ae:
            for doc in params['documents']:
                letter = self.browse(doc['letter_id'])
                letter.state = 'error'
                letter.error_code = 'UNKNOWN_ERROR'
            raise ae
        for doc in response['request']['documents']:
            if doc.get('sent') and response['request_code'] == 200:
                self.env['iap.account']._send_success_notification(
                    message=_("Snail Mails are successfully sent"))
                note = _('The document was correctly sent by post.<br>The tracking id is %s', doc['send_id'])
                letter_data = {'info_msg': note, 'state': 'sent', 'error_code': False}
                notification_data = {
                    'notification_status': 'sent',
                    'failure_type': False,
                    'failure_reason': False,
                }
            else:
                error = doc['error'] if response['request_code'] == 200 else response['reason']

                if error == 'CREDIT_ERROR':
                    self.env['iap.account']._send_no_credit_notification(
                        service_name='snailmail',
                        title=_("Not enough credits for Snail Mail"))
                note = _('An error occurred when sending the document by post.<br>Error: %s', self._get_error_message(error))
                letter_data = {
                    'info_msg': note,
                    'state': 'error',
                    'error_code': error if error in ERROR_CODES else 'UNKNOWN_ERROR'
                }
                notification_data = {
                    'notification_status': 'exception',
                    'failure_type': self._get_failure_type(error),
                    'failure_reason': note,
                }

            letter = self.browse(doc['letter_id'])
            letter.write(letter_data)
            letter.notification_ids.sudo().write(notification_data)
        self.message_id._notify_message_notification_update()

    def snailmail_print(self):
        self.write({'state': 'pending'})
        self.notification_ids.sudo().write({
            'notification_status': 'ready',
            'failure_type': False,
            'failure_reason': False,
        })
        self.message_id._notify_message_notification_update()
        if len(self) == 1:
            self._snailmail_print()

    def cancel(self):
        self.write({'state': 'canceled', 'error_code': False})
        self.notification_ids.sudo().write({
            'notification_status': 'canceled',
        })
        self.message_id._notify_message_notification_update()

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
    def _is_valid_address(self, record):
        record.ensure_one()
        required_keys = ['street', 'city', 'zip', 'country_id']
        return all(record[key] for key in required_keys)

    def _get_cover_address_split(self):
        address_split = self.partner_id.with_context(show_address=True, lang='en_US').display_name.split('\n')
        if self.country_id.code == 'DE':
            # Germany requires specific address formatting for Pingen
            if self.street2:
                address_split[1] = f'{self.street} // {self.street2}'
            address_split[2] = f'{self.zip} {self.city}'
        return address_split

    def _append_cover_page(self, invoice_bin: bytes):
        out_writer = PdfFileWriter()
        address_split = self._get_cover_address_split()
        address_split[0] = self.partner_id.name or self.partner_id.parent_id and self.partner_id.parent_id.name or address_split[0]
        address = '<br/>'.join(address_split)
        address_x = 118 * mm
        address_y = 60 * mm
        frame_width = 85.5 * mm
        frame_height = 25.5 * mm

        cover_buf = io.BytesIO()
        canvas = Canvas(cover_buf, pagesize=A4)
        styles = getSampleStyleSheet()

        frame = Frame(address_x, A4[1] - address_y - frame_height, frame_width, frame_height)
        story = [Paragraph(address, styles['Normal'])]
        address_inframe = KeepInFrame(0, 0, story)
        frame.addFromList([address_inframe], canvas)
        canvas.save()
        cover_buf.seek(0)

        invoice = PdfFileReader(io.BytesIO(invoice_bin))
        cover_bin = io.BytesIO(cover_buf.getvalue())
        cover_file = PdfFileReader(cover_bin)
        out_writer.appendPagesFromReader(cover_file)

        # Add a blank buffer page to avoid printing behind the cover page
        if self.duplex:
            out_writer.addBlankPage()

        out_writer.appendPagesFromReader(invoice)

        out_buff = io.BytesIO()
        out_writer.write(out_buff)
        return out_buff.getvalue()

    def _overwrite_margins(self, invoice_bin: bytes):
        """
        Fill the margins with white for validation purposes.
        """
        pdf_buf = io.BytesIO()
        canvas = Canvas(pdf_buf, pagesize=A4)
        canvas.setFillColorRGB(255, 255, 255)
        page_width = A4[0]
        page_height = A4[1]

        # Horizontal Margin
        hmargin_width = page_width
        hmargin_height = 5 * mm

        # Vertical Margin
        vmargin_width = 5 * mm
        vmargin_height = page_height

        # Bottom left square
        sq_width = 15 * mm

        # Draw the horizontal margins
        canvas.rect(0, 0, hmargin_width, hmargin_height, stroke=0, fill=1)
        canvas.rect(0, page_height, hmargin_width, -hmargin_height, stroke=0, fill=1)

        # Draw the vertical margins
        canvas.rect(0, 0, vmargin_width, vmargin_height, stroke=0, fill=1)
        canvas.rect(page_width, 0, -vmargin_width, vmargin_height, stroke=0, fill=1)

        # Draw the bottom left white square
        canvas.rect(0, 0, sq_width, sq_width, stroke=0, fill=1)
        canvas.save()
        pdf_buf.seek(0)

        new_pdf = PdfFileReader(pdf_buf)
        curr_pdf = PdfFileReader(io.BytesIO(invoice_bin))
        out = PdfFileWriter()
        for page in curr_pdf.pages:
            page.mergePage(new_pdf.getPage(0))
            out.addPage(page)
        out_stream = io.BytesIO()
        out.write(out_stream)
        out_bin = out_stream.getvalue()
        out_stream.close()
        return out_bin
