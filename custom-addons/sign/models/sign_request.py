# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import base64
import io
import os
import time
import unicodedata
import uuid

from PyPDF2 import PdfFileReader, PdfFileWriter
try:
    from PyPDF2.errors import PdfReadError
except ImportError:
    from PyPDF2.utils import PdfReadError
from reportlab.lib.utils import ImageReader
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.rl_config import TTFSearchPath
from reportlab.pdfgen import canvas
from reportlab.platypus import Paragraph
from reportlab.lib.styles import ParagraphStyle
from reportlab.pdfbase.pdfmetrics import stringWidth
from werkzeug.urls import url_join, url_quote, url_encode
from random import randint
from markupsafe import Markup
from hashlib import sha256
from PIL import UnidentifiedImageError
from dateutil.relativedelta import relativedelta
from datetime import timedelta

from odoo import api, fields, models, http, _, Command
from odoo.tools import config, email_normalize, get_lang, is_html_empty, format_date, formataddr, groupby, consteq
from odoo.exceptions import UserError, ValidationError
from odoo.tools.misc import hmac

TTFSearchPath.append(os.path.join(config["root_path"], "..", "addons", "web", "static", "fonts", "sign"))


def _fix_image_transparency(image):
    """ Modify image transparency to minimize issue of grey bar artefact.

    When an image has a transparent pixel zone next to white pixel zone on a
    white background, this may cause on some renderer grey line artefacts at
    the edge between white and transparent.

    This method sets transparent pixel to white transparent pixel which solves
    the issue for the most probable case. With this the issue happen for a
    black zone on black background but this is less likely to happen.
    """
    pixels = image.load()
    for x in range(image.size[0]):
        for y in range(image.size[1]):
            if pixels[x, y] == (0, 0, 0, 0):
                pixels[x, y] = (255, 255, 255, 0)

class SignRequest(models.Model):
    _name = "sign.request"
    _description = "Signature Request"
    _rec_name = 'reference'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    def _default_access_token(self):
        return str(uuid.uuid4())

    def _expand_states(self, states, domain, order):
        return [key for key, val in self._fields['state'].selection]

    def _get_mail_link(self, email, subject):
        return "mailto:%s?subject=%s" % (url_quote(email), url_quote(subject))

    template_id = fields.Many2one('sign.template', string="Template", required=True)
    subject = fields.Char(string="Email Subject")
    reference = fields.Char(required=True, string="Document Name", help="This is how the document will be named in the mail")

    access_token = fields.Char('Security Token', required=True, default=_default_access_token, readonly=True, copy=False)
    share_link = fields.Char(string="Share Link", compute='_compute_share_link')

    request_item_ids = fields.One2many('sign.request.item', 'sign_request_id', string="Signers", copy=True)
    state = fields.Selection([
        ("shared", "Shared"),
        ("sent", "Sent"),
        ("signed", "Fully Signed"),
        ("refused", "Refused"),
        ("canceled", "Canceled"),
        ("expired", "Expired"),
    ], default='sent', tracking=True, group_expand='_expand_states', copy=False, index=True)

    completed_document = fields.Binary(readonly=True, string="Completed Document", attachment=True, copy=False)

    nb_wait = fields.Integer(string="Sent Requests", compute="_compute_stats", store=True)
    nb_closed = fields.Integer(string="Completed Signatures", compute="_compute_stats", store=True)
    nb_total = fields.Integer(string="Requested Signatures", compute="_compute_stats", store=True)
    progress = fields.Char(string="Progress", compute="_compute_progress", compute_sudo=True)
    start_sign = fields.Boolean(string="Signature Started", help="At least one signer has signed the document.", compute="_compute_progress", compute_sudo=True)
    integrity = fields.Boolean(string="Integrity of the Sign request", compute='_compute_hashes', compute_sudo=True)

    active = fields.Boolean(default=True, string="Active", copy=False)
    favorited_ids = fields.Many2many('res.users', string="Favorite of")

    color = fields.Integer()
    request_item_infos = fields.Binary(compute="_compute_request_item_infos")
    last_action_date = fields.Datetime(related="message_ids.create_date", readonly=True, string="Last Action Date")
    completion_date = fields.Date(string="Completion Date", compute="_compute_progress", compute_sudo=True)
    communication_company_id = fields.Many2one('res.company', string="Company used for communication", default=lambda self: self.env.company)

    sign_log_ids = fields.One2many('sign.log', 'sign_request_id', string="Logs", help="Activity logs linked to this request")
    template_tags = fields.Many2many('sign.template.tag', string='Tags')
    cc_partner_ids = fields.Many2many('res.partner', string='Copy to', compute='_compute_cc_partners')
    message = fields.Html('sign.message')
    message_cc = fields.Html('sign.message_cc')
    attachment_ids = fields.Many2many('ir.attachment', string='Attachments', readonly=True, copy=False, ondelete="restrict")
    completed_document_attachment_ids = fields.Many2many('ir.attachment', 'sign_request_completed_document_rel', string='Completed Documents', readonly=True, copy=False, ondelete="restrict")

    need_my_signature = fields.Boolean(compute='_compute_need_my_signature', search='_search_need_my_signature')

    validity = fields.Date(string='Valid Until')
    reminder = fields.Integer(string='Reminder', default=0)
    last_reminder = fields.Date(string='Last reminder', default=lambda self: fields.Date.today())

    @api.depends_context('uid')
    def _compute_need_my_signature(self):
        my_partner_id = self.env.user.partner_id
        for sign_request in self:
            sign_request.need_my_signature = any(sri.partner_id.id == my_partner_id.id and sri.state == 'sent' and sri.is_mail_sent for sri in sign_request.request_item_ids)

    @api.model
    def _search_need_my_signature(self, operator, value):
        my_partner_id = self.env.user.partner_id
        if operator not in ['=', '!='] or not isinstance(value, bool):
            return []
        domain_operator = 'not in' if (operator == '=') ^ value else 'in'
        documents_ids = self.env['sign.request.item'].search([('partner_id', '=', my_partner_id.id), ('state', '=', 'sent'), ('is_mail_sent', '=', True)]).mapped('sign_request_id').ids
        return [('id', domain_operator, documents_ids)]

    @api.depends('request_item_ids.state')
    def _compute_stats(self):
        for rec in self:
            rec.nb_total = len(rec.request_item_ids)
            rec.nb_wait = len(rec.request_item_ids.filtered(lambda sri: sri.state == 'sent'))
            rec.nb_closed = rec.nb_total - rec.nb_wait

    @api.depends('request_item_ids.state')
    def _compute_progress(self):
        for rec in self:
            rec.start_sign = bool(rec.nb_closed)
            rec.progress = "{} / {}".format(rec.nb_closed, rec.nb_total)
            rec.completion_date = rec.request_item_ids.sorted(key="signing_date", reverse=True)[:1].signing_date if not rec.nb_wait else None

    @api.depends('request_item_ids.state', 'request_item_ids.partner_id.name')
    def _compute_request_item_infos(self):
        for request in self:
            request.request_item_infos = [{
                'id': item.id,
                'partner_name': item.display_name,
                'state': item.state,
                'signing_date': item.signing_date or ''
            } for item in request.request_item_ids]

    @api.depends('message_follower_ids.partner_id')
    def _compute_cc_partners(self):
        for sign_request in self:
            sign_request.cc_partner_ids = sign_request.message_follower_ids.partner_id - sign_request.request_item_ids.partner_id

    @api.depends('request_item_ids.access_token')
    def _compute_share_link(self):
        for sign_request in self.filtered(lambda sr: sr.state == 'shared'):
            sign_request.share_link = "%s/sign/document/mail/%s/%s" % (self.get_base_url(), sign_request.id, sign_request.request_item_ids[0].sudo().access_token)

    @api.model_create_multi
    def create(self, vals_list):
        sign_requests = super().create(vals_list)
        sign_requests.template_id._check_send_ready()
        for sign_request in sign_requests:
            if not sign_request.request_item_ids:
                raise ValidationError(_("A valid sign request needs at least one sign request item"))
            sign_request.template_tags = [Command.set(sign_request.template_id.tag_ids.ids)]
            sign_request.attachment_ids.write({'res_model': sign_request._name, 'res_id': sign_request.id})
            sign_request.message_subscribe(partner_ids=sign_request.request_item_ids.partner_id.ids)
            self.env['sign.log'].sudo().create({'sign_request_id': sign_request.id, 'action': 'create'})
        if not self._context.get('no_sign_mail'):
            sign_requests.send_signature_accesses()
        return sign_requests

    def copy(self, default=None):
        self.ensure_one()
        default = default or {}
        if 'attachment_ids' not in default:
            default['attachment_ids'] = [attachment.copy().id for attachment in self.attachment_ids]
        sign_request = super().copy(default)
        sign_request.message_subscribe(partner_ids=self.cc_partner_ids.ids)
        return sign_request

    def toggle_active(self):
        self.filtered(lambda sr: sr.active and sr.state == 'sent').cancel()
        super(SignRequest, self).toggle_active()

    def _check_senders_validity(self):
        invalid_senders = self.create_uid.filtered(lambda u: not u.email_formatted)
        if invalid_senders:
            raise ValidationError(_("Please configure senders'(%s) email addresses", ', '.join(invalid_senders.mapped('name'))))

    def _check_signers_roles_validity(self):
        for sign_request in self:
            template_roles = sign_request.sudo().template_id.sign_item_ids.responsible_id
            sign_request_items = sign_request.request_item_ids
            if len(sign_request_items) != max(len(template_roles), 1) or \
                    set(sign_request_items.role_id.ids) != (set(template_roles.ids) if template_roles else set([self.env.ref('sign.sign_item_role_default').id])):
                raise ValidationError(_("You must specify one signer for each role of your sign template"))

    def _check_signers_partners_validity(self):
        for sign_request in self:
            sign_request_items = sign_request.request_item_ids
            if sign_request.state == 'shared' and (len(sign_request_items) != 1 or sign_request_items.partner_id):
                raise ValidationError(_("A shared sign request should only have one signer with an empty partner"))
            if sign_request.state != 'shared' and any(not sri.partner_id for sri in sign_request_items):
                raise ValidationError(_("A non-shared sign request's should not have any signer with an empty partner"))

    def _get_final_recipients(self):
        all_recipients = set(self.request_item_ids.mapped('signer_email')) | \
                         set(self.cc_partner_ids.filtered(lambda p: p.email_formatted).mapped('email'))
        return all_recipients

    def _get_next_sign_request_items(self):
        self.ensure_one()
        sign_request_items_sent = self.request_item_ids.filtered(lambda sri: sri.state == 'sent')
        if not sign_request_items_sent:
            return self.env['sign.request.item']
        smallest_order = min(sign_request_items_sent.mapped('mail_sent_order'))
        next_request_items = sign_request_items_sent.filtered(lambda sri: sri.mail_sent_order == smallest_order)
        return next_request_items

    def go_to_document(self):
        self.ensure_one()
        request_items = self.request_item_ids.filtered(lambda r: not r.partner_id or (r.state == 'sent' and r.partner_id.id == self.env.user.partner_id.id))
        return {
            'name': self.reference,
            'type': 'ir.actions.client',
            'tag': 'sign.Document',
            'context': {
                'id': self.id,
                'token': self.access_token,
                'need_to_sign': bool(request_items),
                'create_uid': self.create_uid.id,
                'state': self.state,
                'request_item_states': {str(item.id): item.is_mail_sent for item in self.request_item_ids},
            },
        }

    def go_to_signable_document(self, request_items=None):
        """ go to the signable document as the signers for specified request_items or the current user"""
        self.ensure_one()
        if not request_items:
            request_items = self.request_item_ids.filtered(lambda r: not r.partner_id or (r.state == 'sent' and r.partner_id.id == self.env.user.partner_id.id))
        if not request_items:
            return
        return {
            'name': self.reference,
            'type': 'ir.actions.client',
            'tag': 'sign.SignableDocument',
            'context': {
                'id': self.id,
                'token': request_items[:1].sudo().access_token,
                'create_uid': self.create_uid.id,
                'state': self.state,
                'request_item_states': {item.id: item.is_mail_sent for item in self.request_item_ids},
                'template_editable': self.nb_closed == 0,
                'token_list': request_items[1:].sudo().mapped('access_token'),
                'name_list': [item.partner_id.name for item in request_items[1:]],
            },
        }

    def open_template(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": _("Templates"),
            "res_model": "sign.template",
            "domain": [["id", "=", self.template_id.id], ["active", "=", self.template_id.active]],
            "views": [[False, 'kanban']]
        }

    def get_completed_document(self):
        if not self:
            raise UserError(_('You should select at least one document to download.'))

        if len(self) < 2:
            return {
                'name': 'Signed Document',
                'type': 'ir.actions.act_url',
                'url': '/sign/download/%(request_id)s/%(access_token)s/completed' % {'request_id': self.id, 'access_token': self.access_token},
            }
        else:
            return {
                'name': 'Signed Documents',
                'type': 'ir.actions.act_url',
                'url': f'/sign/download/zip/{",".join(map(str, self.ids))}',
            }

    def open_logs(self):
        self.ensure_one()
        return {
            "name": _("Activity Logs"),
            "type": "ir.actions.act_window",
            "res_model": "sign.log",
            'view_mode': 'tree,form',
            'domain': [('sign_request_id', '=', self.id)],
        }

    @api.onchange("progress", "start_sign")
    def _compute_hashes(self):
        for document in self:
            try:
                document.integrity = self.sign_log_ids._check_document_integrity()
            except Exception:
                document.integrity = False

    def toggle_favorited(self):
        self.ensure_one()
        self.write({'favorited_ids': [(3 if self.env.user in self.favorited_ids else 4, self.env.user.id)]})

    def _refuse(self, refuser, refusal_reason):
        """ Refuse a SignRequest. It can only be used in SignRequestItem._refuse
        :param res.partner refuser: the refuser who refuse to sign
        :param str refusal_reason: the refusal reason provided by the refuser
        """
        self.ensure_one()
        if self.state != 'sent':
            raise UserError(_("This sign request cannot be refused"))
        self._check_senders_validity()
        self.write({'state': 'refused'})
        self.request_item_ids._cancel(no_access=False)

        # cancel request and activities for other unsigned users
        for user in self.request_item_ids.partner_id.user_ids.filtered(lambda u: u.has_group('sign.group_sign_user')):
            self.activity_unlink(['mail.mail_activity_data_todo'], user_id=user.id)

        # send emails to signers and cc_partners
        for sign_request_item in self.request_item_ids:
            self._send_refused_mail(refuser, refusal_reason, sign_request_item.partner_id, access_token=sign_request_item.sudo().access_token, force_send=True)
        for partner in self.cc_partner_ids.filtered(lambda p: p.email_formatted) - self.request_item_ids.partner_id:
            self._send_refused_mail(refuser, refusal_reason, partner)

    def _send_refused_mail(self, refuser, refusal_reason, partner, access_token=None, force_send=False):
        self.ensure_one()
        if access_token is None:
            access_token = self.access_token
        subject = _("The document (%s) has been rejected by one of the signers", self.template_id.name)
        base_url = self.get_base_url()
        partner_lang = get_lang(self.env, lang_code=partner.lang).code
        body = self.env['ir.qweb']._render('sign.sign_template_mail_refused', {
            'record': self,
            'recipient': partner,
            'refuser': refuser,
            'link': url_join(base_url, 'sign/document/%s/%s' % (self.id, access_token)),
            'subject': subject,
            'body': Markup('<p style="white-space: pre">{}</p>').format(refusal_reason),
        }, lang=partner_lang, minimal_qcontext=True)

        self._message_send_mail(
            body, 'mail.mail_notification_light',
            {'record_name': self.reference},
            {'model_description': 'signature', 'company': self.communication_company_id or self.create_uid.company_id},
            {'email_from': self.create_uid.email_formatted,
             'author_id': self.create_uid.partner_id.id,
             'email_to': partner.email_formatted,
             'subject': subject},
            force_send=force_send,
            lang=partner_lang,
        )

    def send_signature_accesses(self):
        # Send/Resend accesses for 'sent' sign.request.items by email
        allowed_request_ids = self.filtered(lambda sr: sr.state == 'sent')
        allowed_request_ids._check_senders_validity()
        for sign_request in allowed_request_ids:
            sign_request._get_next_sign_request_items().send_signature_accesses()
            sign_request.last_reminder = fields.Date.today()

    @api.model
    def _cron_reminder(self):
        today = fields.Date.today()
        # find all expired sign requests and those that need a reminder
        # in one query, the code will handle them differently
        # note: archived requests are not fetched.
        self.env.cr.execute(f'''
        SELECT id 
        FROM sign_request sr
        WHERE sr.state = 'sent'
        AND active = TRUE
        AND (
            sr.validity < '{today}' 
            OR (sr.reminder > 0 AND sr.last_reminder + sr.reminder * ('1 day'::interval) <= '{today}')
        )
        ''')
        res = self.env.cr.fetchall()
        request_to_send = self.env['sign.request']
        for request in self.browse(v[0] for v in res):
            if request.validity < today:
                request.state = 'expired'
            else:
                request_to_send += request
        request_to_send.with_context(force_send=False).send_signature_accesses()

    def _sign(self):
        """ Sign a SignRequest. It can only be used in the SignRequestItem._sign """
        self.ensure_one()
        if self.state != 'sent' or any(sri.state != 'completed' for sri in self.request_item_ids):
            raise UserError(_("This sign request cannot be signed"))
        self.write({'state': 'signed'})
        if not bool(config['test_enable'] or config['test_file']):
            self.env.cr.commit()
        if not self._check_is_encrypted():
            # if the file is encrypted, we must wait that the document is decrypted
            self._send_completed_document()

    def _check_is_encrypted(self):
        self.ensure_one()
        if not self.template_id.sign_item_ids:
            return False

        old_pdf = PdfFileReader(io.BytesIO(base64.b64decode(self.template_id.attachment_id.datas)), strict=False, overwriteWarnings=False)
        return old_pdf.isEncrypted

    def cancel(self):
        for sign_request in self:
            sign_request.write({'access_token': self._default_access_token(), 'state': 'canceled'})
        self.request_item_ids._cancel()

        # cancel activities for signers
        for user in self.request_item_ids.sudo().partner_id.user_ids.filtered(lambda u: u.has_group('sign.group_sign_user')):
            self.activity_unlink(['mail.mail_activity_data_todo'], user_id=user.id)

        self.env['sign.log'].sudo().create([{'sign_request_id': sign_request.id, 'action': 'cancel'} for sign_request in self])

    def _send_completed_document(self):
        """ Send the completed document to signers and Contacts in copy with emails
        """
        self.ensure_one()
        if self.state != 'signed':
            raise UserError(_('The sign request has not been fully signed'))
        self._check_senders_validity()

        if not self.completed_document:
            self._generate_completed_document()

        signers = [{'name': signer.partner_id.name, 'email': signer.signer_email, 'id': signer.partner_id.id} for signer in self.request_item_ids]
        request_edited = any(log.action == "update" for log in self.sign_log_ids)
        for sign_request_item in self.request_item_ids:
            self._send_completed_document_mail(signers, request_edited, sign_request_item.partner_id, access_token=sign_request_item.sudo().access_token, with_message_cc=False, force_send=True)

        cc_partners_valid = self.cc_partner_ids.filtered(lambda p: p.email_formatted)
        for cc_partner in cc_partners_valid:
            self._send_completed_document_mail(signers, request_edited, cc_partner)
        if cc_partners_valid:
            body = _("The mail has been sent to contacts in copy: ") + ', '.join(cc_partners_valid.mapped('name'))
            if not is_html_empty(self.message_cc):
                body += self.message_cc
            self.message_post(body=body, attachment_ids=self.attachment_ids.ids + self.completed_document_attachment_ids.ids)

    def _send_completed_document_mail(self, signers, request_edited, partner, access_token=None, with_message_cc=True, force_send=False):
        self.ensure_one()
        if access_token is None:
            access_token = self.access_token
        partner_lang = get_lang(self.env, lang_code=partner.lang).code
        base_url = self.get_base_url()
        body = self.env['ir.qweb']._render('sign.sign_template_mail_completed', {
            'record': self,
            'link': url_join(base_url, 'sign/document/%s/%s' % (self.id, access_token)),
            'subject': '%s signed' % self.reference,
            'body': self.message_cc if with_message_cc and not is_html_empty(self.message_cc) else False,
            'recipient_name': partner.name,
            'recipient_id': partner.id,
            'signers': signers,
            'request_edited': request_edited,
            }, lang=partner_lang, minimal_qcontext=True)

        self.env['sign.request']._message_send_mail(
            body, 'mail.mail_notification_light',
            {'record_name': self.reference},
            {'model_description': 'signature', 'company': self.communication_company_id or self.create_uid.company_id},
            {'email_from': self.create_uid.email_formatted,
             'author_id': self.create_uid.partner_id.id,
             'email_to': partner.email_formatted,
             'subject': _('%s has been edited and signed', self.reference) if request_edited else _('%s has been signed', self.reference),
             'attachment_ids': self.attachment_ids.ids + self.completed_document_attachment_ids.ids},
            force_send=force_send,
            lang=partner_lang,
        )

    def _get_font(self):
        custom_font = self.env["ir.config_parameter"].sudo().get_param("sign.use_custom_font")
        # The font must be a TTF font. The tool 'otf2ttf' may be useful for conversion.
        if custom_font:
            pdfmetrics.registerFont(TTFont(custom_font, custom_font + ".ttf"))
            return custom_font
        return "Helvetica"

    def _get_normal_font_size(self):
        return 0.015

    def _get_displayed_text(self, text):
        """
        Display the text based on his first character unicode name to choose Right-to-left or Left-to-right
        This is just a hotfix to make things work
        In the future the clean way be to use arabic-reshaper and python3-bidi libraries


        Here we want to check the text is in a right-to-left language and if then, flip before returning it.
        Depending on the language, the type should be Left-to-Right, Right-to-Left, or Right-to-Left Arabic
        (Refer to this https://www.unicode.org/reports/tr9/#Bidirectional_Character_Types)
        The base module ```unicodedata``` with his function ```bidirectional(str)``` helps us by taking a character in
        argument and returns his type:
        - 'L' for Left-to-Right character
        - 'R' or 'AL' for Right-to-Left character

        So we have to check if the first character of the text is of type 'R' or 'AL', and check that there is no
        character in the rest of the text that is of type 'L'. Based on that we can confirm we have a fully Right-to-Left language,
        then we can flip the text before returning it.
        """
        if not text:
            return ''
        maybe_rtl_letter = text.lstrip()[:1] or ' '
        maybe_ltr_text = text[1:]
        first_letter_is_rtl = unicodedata.bidirectional(maybe_rtl_letter) in ('AL', 'R')
        no_letter_is_ltr = not any(unicodedata.bidirectional(letter) == 'L' for letter in maybe_ltr_text)
        if first_letter_is_rtl and no_letter_is_ltr:
            text = text[::-1]

        return text

    @staticmethod
    def get_page_size(pdf_reader):
        first_page = pdf_reader.pages and pdf_reader.pages[0]
        media_box = first_page and first_page.mediaBox
        width = media_box and media_box.getWidth()
        height = media_box and media_box.getHeight()

        return (width, height) if width and height else None

    def _generate_completed_document(self, password=""):
        self.ensure_one()
        if self.state != 'signed':
            raise UserError(_("The completed document cannot be created because the sign request is not fully signed"))
        if not self.template_id.sign_item_ids:
            self.completed_document = self.template_id.attachment_id.datas
        else:
            try:
                old_pdf = PdfFileReader(io.BytesIO(base64.b64decode(self.template_id.attachment_id.datas)), strict=False, overwriteWarnings=False)
                old_pdf.getNumPages()
            except:
                raise ValidationError(_("ERROR: Invalid PDF file!"))

            isEncrypted = old_pdf.isEncrypted
            if isEncrypted and not old_pdf.decrypt(password):
                # password is not correct
                return

            font = self._get_font()
            normalFontSize = self._get_normal_font_size()

            packet = io.BytesIO()
            can = canvas.Canvas(packet, pagesize=self.get_page_size(old_pdf))
            itemsByPage = self.template_id._get_sign_items_by_page()
            items_ids = [id for items in itemsByPage.values() for id in items.ids]
            values_dict = self.env['sign.request.item.value']._read_group(
                [('sign_item_id', 'in', items_ids), ('sign_request_id', '=', self.id)],
                groupby=['sign_item_id'],
                aggregates=['value:array_agg', 'frame_value:array_agg', 'frame_has_hash:array_agg']
            )
            values = {
                sign_item.id : {
                    'value': values[0],
                    'frame': frame_values[0],
                    'frame_has_hash': frame_has_hashes[0],
                }
                for sign_item, values, frame_values, frame_has_hashes in values_dict
            }

            for p in range(0, old_pdf.getNumPages()):
                page = old_pdf.getPage(p)
                # Absolute values are taken as it depends on the MediaBox template PDF metadata, they may be negative
                width = float(abs(page.mediaBox.getWidth()))
                height = float(abs(page.mediaBox.getHeight()))

                # Set page orientation (either 0, 90, 180 or 270)
                rotation = page['/Rotate'] if '/Rotate' in page else 0
                if rotation and isinstance(rotation, int):
                    can.rotate(rotation)
                    # Translate system so that elements are placed correctly
                    # despite of the orientation
                    if rotation == 90:
                        width, height = height, width
                        can.translate(0, -height)
                    elif rotation == 180:
                        can.translate(-width, -height)
                    elif rotation == 270:
                        width, height = height, width
                        can.translate(-width, 0)

                items = itemsByPage[p + 1] if p + 1 in itemsByPage else []
                for item in items:
                    value_dict = values.get(item.id)
                    if not value_dict:
                        continue
                    # only get the 1st
                    value = value_dict['value']
                    frame = value_dict['frame']

                    if frame:
                        try:
                            image_reader = ImageReader(io.BytesIO(base64.b64decode(frame[frame.find(',')+1:])))
                        except UnidentifiedImageError:
                            raise ValidationError(_("There was an issue downloading your document. Please contact an administrator."))
                        _fix_image_transparency(image_reader._image)
                        can.drawImage(
                            image_reader,
                            width*item.posX,
                            height*(1-item.posY-item.height),
                            width*item.width,
                            height*item.height,
                            'auto',
                            True
                        )

                    if item.type_id.item_type == "text":
                        value = self._get_displayed_text(value)
                        can.setFont(font, height*item.height*0.8)
                        if item.alignment == "left":
                            can.drawString(width*item.posX, height*(1-item.posY-item.height*0.9), value)
                        elif item.alignment == "right":
                            can.drawRightString(width*(item.posX+item.width), height*(1-item.posY-item.height*0.9), value)
                        else:
                            can.drawCentredString(width*(item.posX+item.width/2), height*(1-item.posY-item.height*0.9), value)

                    elif item.type_id.item_type == "selection":
                        content = []
                        for option in item.option_ids:
                            if option.id != int(value):
                                content.append("<strike>%s</strike>" % (option.value))
                            else:
                                content.append(option.value)
                        font_size = height * normalFontSize * 0.8
                        text = " / ".join(content)
                        string_width = stringWidth(text.replace("<strike>", "").replace("</strike>", ""), font, font_size)
                        p = Paragraph(text, ParagraphStyle(name='Selection Paragraph', fontName=font, fontSize=font_size, leading=12))
                        posX = width * (item.posX + item.width * 0.5) - string_width // 2
                        posY = height * (1 - item.posY - item.height * 0.5) - p.wrap(width, height)[1] // 2
                        p.drawOn(can, posX, posY)

                    elif item.type_id.item_type == "textarea":
                        font_size = height * normalFontSize * 0.8
                        can.setFont(font, font_size)
                        lines = value.split('\n')
                        y = (1-item.posY)
                        for line in lines:
                            empty_space = width * item.width - can.stringWidth(line, font, font_size)
                            x_shift = 0
                            if item.alignment == 'center':
                                x_shift = empty_space / 2
                            elif item.alignment == 'right':
                                x_shift = empty_space
                            y -= normalFontSize * 0.9
                            can.drawString(width * item.posX + x_shift, height * y, line)
                            y -= normalFontSize * 0.1

                    elif item.type_id.item_type == "checkbox":
                        can.setFont(font, height*item.height*0.8)
                        value = 'X' if value == 'on' else ''
                        can.drawString(width*item.posX, height*(1-item.posY-item.height*0.9), value)

                    elif item.type_id.item_type == "signature" or item.type_id.item_type == "initial":
                        try:
                            image_reader = ImageReader(io.BytesIO(base64.b64decode(value[value.find(',')+1:])))
                        except UnidentifiedImageError:
                            raise ValidationError(_("There was an issue downloading your document. Please contact an administrator."))
                        _fix_image_transparency(image_reader._image)
                        can.drawImage(image_reader, width*item.posX, height*(1-item.posY-item.height), width*item.width, height*item.height, 'auto', True)

                can.showPage()

            can.save()

            item_pdf = PdfFileReader(packet, overwriteWarnings=False)
            new_pdf = PdfFileWriter()

            for p in range(0, old_pdf.getNumPages()):
                page = old_pdf.getPage(p)
                page.mergePage(item_pdf.getPage(p))
                new_pdf.addPage(page)

            if isEncrypted:
                new_pdf.encrypt(password)

            try:
                output = io.BytesIO()
                new_pdf.write(output)
            except PdfReadError:
                raise ValidationError(_("There was an issue downloading your document. Please contact an administrator."))

            self.completed_document = base64.b64encode(output.getvalue())
            output.close()

        attachment = self.env['ir.attachment'].create({
            'name': "%s.pdf" % self.reference if self.reference.split('.')[-1] != 'pdf' else self.reference,
            'datas': self.completed_document,
            'type': 'binary',
            'res_model': self._name,
            'res_id': self.id,
        })

        # print the report with the public user in a sudoed env
        # public user because we don't want groups to pollute the result
        # (e.g. if the current user has the group Sign Manager,
        # some private information will be sent to *all* signers)
        # sudoed env because we have checked access higher up the stack
        public_user = self.env.ref('base.public_user', raise_if_not_found=False)
        if not public_user:
            # public user was deleted, fallback to avoid crash (info may leak)
            public_user = self.env.user
        pdf_content, __ = self.env["ir.actions.report"].with_user(public_user).sudo()._render_qweb_pdf(
            'sign.action_sign_request_print_logs',
            self.ids,
            data={'format_date': format_date, 'company_id': self.communication_company_id}
        )
        attachment_log = self.env['ir.attachment'].create({
            'name': "Certificate of completion - %s.pdf" % time.strftime('%Y-%m-%d - %H:%M:%S'),
            'raw': pdf_content,
            'type': 'binary',
            'res_model': self._name,
            'res_id': self.id,
        })
        self.completed_document_attachment_ids = [Command.set([attachment.id, attachment_log.id])]

    @api.model
    def _message_send_mail(self, body, email_layout_xmlid, message_values, notif_values, mail_values, force_send=False, **kwargs):
        """ Shortcut to send an email. """
        default_lang = get_lang(self.env, lang_code=kwargs.get('lang')).code
        lang = kwargs.get('lang', default_lang)
        sign_request = self.with_context(lang=lang)

        # the notif layout wrapping expects a mail.message record, but we don't want
        # to actually create the record
        # See @tde-banana-odoo for details
        msg = sign_request.env['mail.message'].sudo().new(dict(body=body, **message_values))
        body_html = self.env['ir.qweb']._render(email_layout_xmlid, dict(message=msg, **notif_values), minimal_qcontext=True)
        body_html = sign_request.env['mail.render.mixin']._replace_local_links(body_html)

        mail_values['reply_to'] = mail_values.get('email_from')
        mail = sign_request.env['mail.mail'].sudo().create(dict(body_html=body_html, **mail_values))
        if force_send:
            mail.send()
        return mail

    def _schedule_activity(self, sign_users):
        for user in sign_users:
            self.with_context(mail_activity_quick_update=True).activity_schedule(
                'mail.mail_activity_data_todo',
                user_id=user.id
            )


class SignRequestItem(models.Model):
    _name = "sign.request.item"
    _description = "Signature Request Item"
    _inherit = ['portal.mixin']
    _rec_name = 'partner_id'

    def _default_access_token(self):
        return str(uuid.uuid4())

    def _get_mail_link(self, email, subject):
        return "mailto:%s?subject=%s" % (url_quote(email), url_quote(subject))

    # this display_name (with sudo) is used for many2many_tags especially the partner_id is private
    display_name = fields.Char(compute='_compute_display_name', compute_sudo=True)

    partner_id = fields.Many2one('res.partner', string="Signer", ondelete='restrict')
    sign_request_id = fields.Many2one('sign.request', string="Signature Request", ondelete='cascade', required=True, copy=False)
    sign_item_value_ids = fields.One2many('sign.request.item.value', 'sign_request_item_id', string="Value")
    reference = fields.Char(related='sign_request_id.reference', string="Document Name")
    mail_sent_order = fields.Integer(default=1)
    communication_company_id = fields.Many2one(related='sign_request_id.communication_company_id')

    access_token = fields.Char(required=True, default=_default_access_token, readonly=True, copy=False, groups="base.group_system")
    access_via_link = fields.Boolean('Accessed Through Token', copy=False)
    role_id = fields.Many2one('sign.item.role', string="Role", required=True, readonly=True)
    sms_number = fields.Char(related='partner_id.mobile', readonly=False, depends=(['partner_id']), store=True, copy=False)
    sms_token = fields.Char('SMS Token', readonly=True, copy=False)
    signed_without_extra_auth = fields.Boolean('Signed Without Extra Authentication', default=False, readonly=True, copy=False)

    signature = fields.Binary(attachment=True, copy=False)
    frame_hash = fields.Char(size=256, compute='_compute_frame_hash')
    signing_date = fields.Date('Signed on', readonly=True, copy=False)
    state = fields.Selection([
        ("sent", "To Sign"),
        ("refused", "Refused"),
        ("completed", "Completed"),
        ("canceled", "Canceled"),
    ], readonly=True, default="sent", copy=False, index=True)
    color = fields.Integer(compute='_compute_color')
    ignored = fields.Boolean(required=True, default=False, copy=False)

    signer_email = fields.Char(string='Email', compute="_compute_email", store=True)
    is_mail_sent = fields.Boolean(readonly=True, copy=False, help="The signature mail has been sent.")
    change_authorized = fields.Boolean(related='role_id.change_authorized')

    latitude = fields.Float(digits=(10, 7), copy=False)
    longitude = fields.Float(digits=(10, 7), copy=False)

    @api.constrains('signer_email')
    def _check_signer_email_validity(self):
        if any(sri.partner_id and not sri.signer_email for sri in self):
            raise ValidationError(_("All signers must have valid email addresses"))

    @api.constrains('partner_id', 'role_id')
    def _check_signers_validity(self):
        # this check allows one signer to be False, which is used to "share" a sign template
        self.sign_request_id._check_signers_roles_validity()
        self.sign_request_id._check_signers_partners_validity()

    @api.depends('signer_email')
    def _compute_frame_hash(self):
        db_uuid = self.env['ir.config_parameter'].sudo().get_param('database.uuid')
        for sri in self:
            if sri.partner_id:
                sri.frame_hash = sha256((sri.signer_email + db_uuid).encode()).hexdigest()
            else:
                sri.frame_hash = ''

    @api.depends('partner_id.name')
    def _compute_display_name(self):
        for sri in self:
            sri.display_name = sri.partner_id.display_name if sri.partner_id else _('Public User')

    def write(self, vals):
        if vals.get('partner_id') is False:
            raise UserError(_("You need to define a signatory"))
        request_items_reassigned = self.env['sign.request.item']
        if vals.get('partner_id'):
            request_items_reassigned |= self.filtered(lambda sri: sri.partner_id.id != vals['partner_id'])
            if any(sri.state != 'sent'
                   or sri.sign_request_id.state != 'sent'
                   or (sri.partner_id and not sri.role_id.change_authorized)
                   or sri.sign_request_id.state == 'shared'
                   for sri in request_items_reassigned):
                raise UserError(_("You cannot reassign this signatory"))
            new_sign_partner = self.env['res.partner'].browse(vals.get('partner_id'))
            for request_item in request_items_reassigned:
                sign_request = request_item.sign_request_id
                old_sign_user = request_item.partner_id.user_ids[:1]
                # remove old activities for internal users if they are no longer one of the unsigned signers of their sign requests
                if old_sign_user and old_sign_user.has_group('sign.group_sign_user') and \
                        not sign_request.request_item_ids.filtered(
                            lambda sri: sri.partner_id == request_item.partner_id and sri.state == 'sent' and sri not in request_items_reassigned):
                    sign_request.activity_unlink(['mail.mail_activity_data_todo'], user_id=old_sign_user.id)
                # create logs
                sign_request.message_post(
                    body=_('The contact of %(role)s has been changed from %(old_partner)s to %(new_partner)s.',
                           role=request_item.role_id.name, old_partner=request_item.partner_id.name, new_partner=new_sign_partner.name))

            # add new followers
            request_items_reassigned.sign_request_id.message_subscribe(partner_ids=[vals.get('partner_id')])
            # add new activities for internal users
            new_sign_user = self.env['res.users'].search([
                ('partner_id', '=', vals.get('partner_id')),
                ('groups_id', 'in', [self.env.ref('sign.group_sign_user').id])
            ], limit=1)
            if new_sign_user:
                activity_ids = set(request_items_reassigned.sign_request_id.activity_search(['mail.mail_activity_data_todo'], user_id=new_sign_user.id).mapped('res_id'))
                request_items_reassigned.sign_request_id.filtered(lambda sr: sr.id not in activity_ids)._schedule_activity(new_sign_user)

        res = super(SignRequestItem, self).write(vals)

        # change access token
        for request_item in request_items_reassigned.filtered(lambda sri: sri.is_mail_sent):
            request_item.sudo().update({'access_token': self._default_access_token()})
            request_item.is_mail_sent = False
        return res

    def _cancel(self, no_access=True):
        """ Cancel a SignRequestItem. It can only be used in the SignRequest.cancel or SignRequest._refuse
        :param bool no_access: Whether the sign request item cannot be accessed by the previous link in the email
        """
        for request_item in self:
            request_item.write({
                'state': 'canceled' if request_item.state == 'sent' else request_item.state,
                'signing_date': fields.Date.context_today(self) if request_item.state == 'sent' else request_item.signing_date,
                'is_mail_sent': False if no_access else request_item.is_mail_sent,
            })
            request_item.sudo().write({'access_token': self._default_access_token() if no_access else request_item.access_token})

    def _refuse(self, refusal_reason):
        self.ensure_one()
        if not self.env.su:
            raise UserError(_("This function can only be called with sudo."))
        if self.state != 'sent' or self.sign_request_id.state != 'sent':
            raise UserError(_("This sign request item cannot be refused"))
        self.env['sign.log'].create({'sign_request_item_id': self.id, 'action': 'refuse'})
        self.write({'signing_date': fields.Date.context_today(self), 'state': 'refused'})
        refuse_user = self.partner_id.user_ids[:1]
        # mark the activity as done for the refuser
        if refuse_user and refuse_user.has_group('sign.group_sign_user'):
            self.sign_request_id.activity_feedback(['mail.mail_activity_data_todo'], user_id=refuse_user.id)
        refusal_reason = _("No specified reason") if not refusal_reason or refusal_reason.isspace() else refusal_reason
        message_post = _("The signature has been refused by %s(%s)", self.partner_id.name, self.role_id.name)
        message_post = Markup('{}<p style="white-space: pre">{}</p>').format(message_post, refusal_reason)
        self.sign_request_id.message_post(body=message_post)
        self.sign_request_id._refuse(self.partner_id, refusal_reason)

    def _send_signature_access_mail(self):
        for signer in self:
            signer_email_normalized = email_normalize(signer.signer_email or '')
            signer_lang = get_lang(self.env, lang_code=signer.partner_id.lang).code
            context = {'lang': signer_lang}
            # We hide the validity information if it is the default (6 month from the create_date)
            has_default_validity = signer.sign_request_id.validity and signer.sign_request_id.validity - relativedelta(months=6) == signer.sign_request_id.create_date.date()
            expiry_link_timestamp = signer._generate_expiry_link_timestamp()
            url_params = url_encode({
                'timestamp': expiry_link_timestamp,
                'exp': signer._generate_expiry_signature(signer.id, expiry_link_timestamp)
            })
            body = self.env['ir.qweb']._render('sign.sign_template_mail_request', {
                'record': signer,
                'link': url_join(signer.get_base_url(), "sign/document/mail/%(request_id)s/%(access_token)s?%(url_params)s" % {'request_id': signer.sign_request_id.id, 'access_token': signer.sudo().access_token, 'url_params': url_params}),
                'subject': signer.sign_request_id.subject,
                'body': signer.sign_request_id.message if not is_html_empty(signer.sign_request_id.message) else False,
                'use_sign_terms': self.env['ir.config_parameter'].sudo().get_param('sign.use_sign_terms'),
                'user_signature': signer.create_uid.signature,
                'show_validity': signer.sign_request_id.validity and not has_default_validity,
            }, lang=signer_lang, minimal_qcontext=True)

            attachment_ids = signer.sign_request_id.attachment_ids.ids
            self.env['sign.request']._message_send_mail(
                body, 'mail.mail_notification_light',
                {'record_name': signer.sign_request_id.reference},
                {'model_description': _('Signature'), 'company': signer.communication_company_id or signer.sign_request_id.create_uid.company_id},
                {'email_from': signer.create_uid.email_formatted,
                 'author_id': signer.create_uid.partner_id.id,
                 'email_to': formataddr((signer.partner_id.name, signer_email_normalized)),
                 'attachment_ids': attachment_ids,
                 'subject': signer.sign_request_id.subject},
                force_send=self.env.context.get('force_send', True),  # only force_send if not from cron
                lang=signer_lang,
            )
            signer.is_mail_sent = True
            del context

    def _edit_and_sign(self, signature, **kwargs):
        """ Sign sign request items at once.
        :param signature: dictionary containing signature values and corresponding ids
        :param dict new_sign_items: {id (str): values (dict)}
            id: negative: negative random itemId(sync_id) in pdfviewer (the sign item is new created in the pdfviewer and should be created)
            values: values to create
        """
        self.ensure_one()
        if not self.env.su:
            raise UserError(_("This function can only be called with sudo."))
        elif self.state != 'sent' or self.sign_request_id.state != 'sent':
            raise UserError(_("This sign request item cannot be signed"))
        elif self.sign_request_id.validity and self.sign_request_id.validity < fields.Date.today():
            raise UserError(_('This sign request is not valid anymore'))

        # edit request template while signing
        new_sign_items = kwargs.get('new_sign_items', False)
        if new_sign_items:
            if any(int(item_id) >= 0 for item_id in new_sign_items):
                raise UserError(_("Existing sign items are not allowed to be changed"))
            if any(item['responsible_id'] != self.role_id.id for item in new_sign_items.values()):
                raise UserError(_("You can only add new items for the current role"))
            sign_request = self.sign_request_id
            if sign_request.nb_closed != 0:
                raise UserError(_("The document has been signed by a signer and cannot be edited"))
            # copy the old template
            old_template = sign_request.template_id
            new_template = old_template.copy({
                'favorited_ids': [Command.link(sign_request.create_uid.id), Command.link(self.env.user.id)],
                'active': False,
                'sign_item_ids': []
            }).sudo(False)
            existing_item_id_map = old_template._copy_sign_items_to(new_template)

            # edit the new template(add new sign items)
            new_item_id_map = new_template.update_from_pdfviewer(new_sign_items)
            sign_request.template_id = new_template
            item_id_map = dict(existing_item_id_map, **new_item_id_map)

            # update the item ids in signature
            new_signature = {}
            for item_id, item_value in signature.items():
                new_item_id = item_id_map[item_id]
                new_signature[new_item_id] = item_value
            signature = new_signature

            self.env['sign.log'].create({'sign_request_id': sign_request.id, 'action': 'update'})
            body = _("The signature request has been edited by: %s.", self.partner_id.name)
            sign_request.message_post(body=body)

        self._sign(signature, **kwargs)


    def _sign(self, signature, **kwargs):
        """ Stores the sign request item values.
        :param signature: dictionary containing signature values and corresponding ids / signature image
        :param validation_required: boolean indicating whether the sign request item will after a further validation process or now
        """
        self.ensure_one()
        if not self.env.su:
            raise UserError(_("This function can only be called with sudo."))
        elif self.state != 'sent' or self.sign_request_id.state != 'sent':
            raise UserError(_("This sign request item cannot be signed"))
        elif self.sign_request_id.validity and self.sign_request_id.validity < fields.Date.today():
            raise UserError(_('This sign request is not valid anymore'))

        required_ids = set(self.sign_request_id.template_id.sign_item_ids.filtered(
            lambda r: r.responsible_id.id == self.role_id.id and r.required).ids)
        signature_ids = {int(k) for k in signature} if isinstance(signature, dict) else set()
        if not (required_ids <= signature_ids):  # Security check
            raise UserError(_("Some required items are not filled"))

        self._fill(signature, **kwargs)
        if not kwargs.get('validation_required', False):
            self._post_fill_request_item()

    def _send_no_credits_email(self):
        partner_lang = get_lang(self.env, lang_code=self.create_uid.partner_id.lang).code
        body = self.env['ir.qweb']._render('sign.sign_template_mail_not_enough_credits', {
            'record': self,
            'recipient_name': self.create_uid.name,
            'subject': '%s signed' % self.reference,
            'signer': self.partner_id,
            'auth_method': dict(self.role_id._fields['auth_method']._description_selection(self.env))[self.role_id.auth_method]
        }, lang=partner_lang, minimal_qcontext=True)

        self.env['sign.request']._message_send_mail(
            body, 'mail.mail_notification_light',
            {'record_name': self.reference},
            {'model_description': 'signature', 'company': self.communication_company_id or self.create_uid.company_id},
            {
                'email_from': self.create_uid.email_formatted,
                'author_id': self.create_uid.partner_id.id,
                'email_to': self.create_uid.email_formatted,
                'subject': _('%s: missing credits for extra-authentication', self.reference)
            },
            force_send=True,
            lang=partner_lang,
        )

    def _post_fill_request_item(self):
        self.env['sign.log'].create({'sign_request_item_id': self.id, 'action': 'sign'})
        self.write({'signing_date': fields.Date.context_today(self), 'state': 'completed'})
        if self.signed_without_extra_auth:
            self._send_no_credits_email()

        # mark signature as done in next activity
        if not self.sign_request_id.request_item_ids.filtered(lambda sri: sri.partner_id == self.partner_id and sri.state == 'sent'):
            sign_user = self.partner_id.user_ids[:1]
            if sign_user and sign_user.has_group('sign.group_sign_user'):
                self.sign_request_id.activity_feedback(['mail.mail_activity_data_todo'], user_id=sign_user.id)
        sign_request = self.sign_request_id
        if all(sri.state == 'completed' for sri in sign_request.request_item_ids):
            sign_request._sign()
        elif all(sri.state == 'completed' for sri in sign_request.request_item_ids.filtered(lambda sri: sri.mail_sent_order == self.mail_sent_order)):
            sign_request.send_signature_accesses()

    def _fill(self, signature, **kwargs):
        """ Stores the sign request item values. (Can be used to pre-fill the document as a hack)
        :param signature: dictionary containing signature values and corresponding ids / signature image
        """
        self.ensure_one()
        if not self.env.su:
            raise UserError(_("This function can only be called with sudo."))
        if self.state != 'sent' or self.sign_request_id.state != 'sent':
            raise UserError(_("This sign request item cannot be filled"))

        authorised_ids = set(self.sign_request_id.template_id.sign_item_ids.filtered(lambda r: r.responsible_id.id == self.role_id.id).ids)
        signature_ids = {int(k) for k in signature} if isinstance(signature, dict) else set()
        if not (signature_ids <= authorised_ids):
            raise UserError(_("Some unauthorised items are filled"))

        if not isinstance(signature, dict):
            self.signature = signature
        else:
            SignItemValue = self.env['sign.request.item.value']
            sign_request = self.sign_request_id
            new_item_values_list = []
            item_values_dict = {str(sign_item_value.sign_item_id.id): sign_item_value for sign_item_value in self.sign_item_value_ids}
            signature_item_ids = set(sign_request.template_id.sign_item_ids.filtered(lambda r: r.type_id.item_type == 'signature').ids)
            for itemId in signature:
                frame = kwargs.get('frame', False)
                if frame and itemId in frame:
                    frame_value = frame[itemId].get('frameValue', False)
                    frame_has_hash = bool(frame[itemId].get('frameHash', False))
                else:
                    frame_value = False
                    frame_has_hash = False
                if itemId not in item_values_dict:
                    new_item_values_list.append({'sign_item_id': int(itemId), 'sign_request_id': sign_request.id,
                                                 'value': signature[itemId], 'frame_value': frame_value,
                                                 'frame_has_hash': frame_has_hash, 'sign_request_item_id': self.id})
                else:
                    item_values_dict[itemId].write({
                        'value': signature[itemId], 'frame_value': frame_value, 'frame_has_hash': frame_has_hash
                    })
                if int(itemId) in signature_item_ids:
                    self.signature = signature[itemId][signature[itemId].find(',')+1:]
            SignItemValue.create(new_item_values_list)

    def send_signature_accesses(self):
        self.sign_request_id._check_senders_validity()
        users = self.partner_id.user_ids
        user_ids = set(users.sudo().search([('groups_id', 'in', self.env.ref('sign.group_sign_user').id), ('id', 'in', users.ids)]).ids)
        for sign_request, sign_request_items_list in groupby(self, lambda sri: sri.sign_request_id):
            notified_users = [sri.partner_id.user_ids[:1]
                              for sri in sign_request_items_list
                              if not sri.is_mail_sent and sri.state == 'sent' and sri.partner_id.user_ids[:1].id in user_ids]
            sign_request._schedule_activity(notified_users)
            body = _("The signature mail has been sent to: ")
            receiver_names = ["%s(%s)" % (sri.partner_id.name, sri.role_id.name) for sri in sign_request_items_list]
            body += ', '.join(receiver_names)
            if not is_html_empty(sign_request.message):
                body += sign_request.message
            if not sign_request.communication_company_id:
                sign_request.communication_company_id = self.env.company
            sign_request.message_post(body=body, attachment_ids=sign_request.attachment_ids.ids)
        self.write({'ignored': False})
        self._send_signature_access_mail()

    def _get_user_signature(self, signature_type='sign_signature'):
        """ Gets the user's stored sign_signature/sign_initials (needs sudo permission)
            :param str signature_type: 'sign_signature' or 'sign_initials'
            :returns bytes or False
        """
        self.ensure_one()
        sign_user = self.partner_id.user_ids[:1]
        if sign_user and signature_type in ['sign_signature', 'sign_initials']:
            return sign_user[signature_type]
        return False

    def _get_user_signature_frame(self, signature_type='sign_signature_frame'):
        """ Gets the user's stored sign_signature/sign_initials (needs sudo permission)
            :param str signature_type: 'sign_signature' or 'sign_initials'
            :returns bytes or False
        """
        self.ensure_one()
        sign_user = self.partner_id.user_ids[:1]
        if sign_user and signature_type in ['sign_signature_frame', 'sign_initials_frame']:
            return sign_user[signature_type]
        return False

    def _reset_sms_token(self):
        for record in self:
            record.sms_token = randint(100000, 999999)

    def _send_sms(self):
        self._reset_sms_token()
        sms_values = [{'body': _('Your confirmation code is %s', rec.sms_token), 'number': rec.sms_number} for rec in self]
        self.env['sms.sms'].sudo().create(sms_values).send()

    def _compute_access_url(self):
        super(SignRequestItem, self)._compute_access_url()
        for signature_request in self:
            signature_request.access_url = '/my/signature/%s' % signature_request.id

    @api.model
    def _generate_expiry_link_timestamp(self):
        duration = int(self.env['ir.config_parameter'].sudo().get_param('sign.link_expiry_duration', 48))
        expiry_date = fields.Datetime.now() + timedelta(hours=duration)
        return int(expiry_date.timestamp())

    @api.model
    def _generate_expiry_signature(self, sign_request_item_id, timestamp):
        return hmac(self.env(su=True), "sign_expiration", (timestamp, sign_request_item_id))

    def _validate_expiry(self, exp_timestamp, exp_hash):
        """ Validates if the expiry code is still valid
        :param float exp_timestamp: a timestamp provided by the user in the URL params
        :param str exp_hash: code provided in the URL to be checked
        """
        self.ensure_one()
        if not (exp_timestamp and exp_hash):
            return False
        exp_timestamp = int(exp_timestamp)
        now = fields.Datetime.now().timestamp()
        if now > exp_timestamp:
            return False
        return consteq(exp_hash, self._generate_expiry_signature(self.id, exp_timestamp))

    @api.depends('state')
    def _compute_color(self):
        color_map = {"canceled": 0,
                     "sent": 0,
                     "refused": 1,
                     "completed": 10}
        for sign_request_item in self:
            sign_request_item.color = color_map[sign_request_item.state]

    @api.depends('partner_id.email')
    def _compute_email(self):
        for sign_request_item in self.filtered(lambda sri: sri.state == "sent" or not sri.signer_email):
            sign_request_item.signer_email = sign_request_item.partner_id.email_normalized


class SignRequestItemValue(models.Model):
    _name = "sign.request.item.value"
    _description = "Signature Item Value"
    _rec_name = 'sign_request_id'

    sign_request_item_id = fields.Many2one('sign.request.item', string="Signature Request item", required=True,
                                           ondelete='cascade')
    sign_item_id = fields.Many2one('sign.item', string="Signature Item", required=True, ondelete='cascade')
    sign_request_id = fields.Many2one(string="Signature Request", required=True, ondelete='cascade', related='sign_request_item_id.sign_request_id')

    value = fields.Text()
    frame_value = fields.Text()
    frame_has_hash = fields.Boolean()
