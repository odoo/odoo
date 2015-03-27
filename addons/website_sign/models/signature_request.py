# -*- coding: utf-8 -*-
from openerp import models, fields, api, _

from openerp.tools import DEFAULT_SERVER_DATE_FORMAT
import time, uuid, re, StringIO, base64
from pyPdf import PdfFileWriter, PdfFileReader
from reportlab.pdfgen import canvas
from reportlab.lib.utils import ImageReader

class signature_request_template(models.Model):
    _name = "signature.request.template"
    _description = "Signature Request Template"
    _rec_name = "attachment_id"

    attachment_id = fields.Many2one('ir.attachment', string="Attachment", required=True, ondelete='cascade')
    signature_item_ids = fields.One2many('signature.item', 'template_id', string="Signature Items")

    archived = fields.Boolean(default=False, string="Archived")
    favorited_ids = fields.Many2many('res.users', string="Favorite of")

    share_link = fields.Char(readonly=True, string="Share Link")

    signature_request_ids = fields.One2many('signature.request', 'template_id', string="Signature Requests")

    @api.multi
    def go_to_custom_template(self):
        return {
            'name': 'Signature Request Template Edit Field URL',
            'type': 'ir.actions.act_url',
            'url': '/sign/template/' + str(self[0].id),
            'target': 'self',
        }

class signature_request(models.Model):
    _name = "signature.request"
    _description = "Document To Sign"
    _rec_name = 'reference'

    _inherit = 'mail.thread'

    template_id = fields.Many2one('signature.request.template', string="Template", required=True)
    reference = fields.Char(required=True, string="Filename")

    @api.multi
    def _default_access_token(self):
        return str(uuid.uuid4())
    access_token = fields.Char('Security Token', required=True, default=_default_access_token, readonly=True)

    request_item_ids = fields.One2many('signature.request.item', 'signature_request_id', string="Signers")
    state = fields.Selection([
        ("draft", "Draft"),
        ("sent", "Sent"),
        ("signed", "Signed"),
        ("canceled", "Canceled")
    ], default='draft', track_visibility='onchange')

    follower_ids = fields.Many2many('res.partner', string="Followers")

    completed_document = fields.Binary(readonly=True, string="Completed Document")

    nb_draft = fields.Integer(string="Draft Requests", compute="_compute_count", store=True)
    nb_wait = fields.Integer(string="Sent Requests", compute="_compute_count", store=True)
    nb_closed = fields.Integer(string="Completed Signatures", compute="_compute_count", store=True)
    progress = fields.Integer(string="Progress", compute="_compute_count")

    archived = fields.Boolean(string="Archived", default=False)
    favorited_ids = fields.Many2many('res.users', string="Favorite of")

    color = fields.Integer()
    isFavorited = fields.Boolean(compute="_is_favorited") # TODO need this because kanban view has not access on web client anymore...
    
    @api.one
    def _is_favorited(self):
        self.isFavorited = self.env.user.id in self.favorited_ids.mapped('id')

    @api.one
    @api.depends('request_item_ids.state')
    def _compute_count(self):
        draft, wait, closed = 0, 0, 0
        for s in self.request_item_ids:
            if s.state == "draft":
                draft += 1
            if s.state == "sent":
                wait += 1
            if s.state == "completed":
                closed += 1
        self.nb_draft = draft
        self.nb_wait = wait
        self.nb_closed = closed

        if self.nb_wait + self.nb_closed <= 0:
            self.progress = 0
        else:
            self.progress = self.nb_closed*100 / (self.nb_wait + self.nb_closed)

    @api.one
    def _check_after_compute(self):
        if self.state == 'draft' and self.nb_draft == 0 and len(self.request_item_ids) > 0: # When a draft partner is deleted
            self.action_sent()
        elif self.state == 'sent':
            if self.nb_draft > 0 or len(self.request_item_ids) == 0: # A draft partner is added or all partner are deleted
                self.action_draft()
            elif self.nb_closed == len(self.request_item_ids) and len(self.request_item_ids) > 0: # All signed
                self.action_signed()
        elif self.state == 'signed' and (self.nb_draft > 0 or len(self.request_item_ids) == 0): # A draft partner is added or all removed
            self.action_draft()

    @api.multi
    def action_draft(self):
        self.write({'completed_document': None, 'access_token': self._default_access_token(), 'state': 'draft'})

    @api.multi
    def action_sent(self, subject=None, message=None):
        self.write({'state': 'sent'})
        for signature_request in self:
            ignored_partners = []
            for request_item in signature_request.request_item_ids:
                if request_item.state != 'draft':
                    ignored_partners.append(request_item.partner_id.id)
            included_request_items = signature_request.request_item_ids.filtered(lambda r: not r.partner_id or r.partner_id.id not in ignored_partners)
            
            if signature_request.send_signature_accesses(subject, message, ignored_partners=ignored_partners)[0]:
                signature_request.send_follower_accesses(self.follower_ids, subject, message)
                included_request_items.action_sent()
            else:
                signature_request.action_draft()

    @api.multi
    def action_signed(self):
        self.write({'state': 'signed'})
        self.send_completed_document()

    @api.multi
    def action_canceled(self):
        self.write({'completed_document': None, 'access_token': self._default_access_token(), 'state': 'canceled'})
        for signature_request in self:
            signature_request.request_item_ids.action_draft()

    @api.one
    def set_signers(self, signers):
        self.request_item_ids.filtered(lambda r: not r.partner_id or not r.role_id).unlink()

        ids_to_remove = []
        for request_item in self.request_item_ids:
            for i in range(0, len(signers)):
                if signers[i]['partner_id'] == request_item.partner_id.id and signers[i]['role'] == request_item.role_id.id:
                    signers.pop(i)
                    break
            else:
                ids_to_remove.append(request_item.id)

        self.env['signature.request.item'].browse(ids_to_remove).unlink()
        for signer in signers:
            self.env['signature.request.item'].create({
                'partner_id': signer['partner_id'],
                'signature_request_id': self.id,
                'role_id': signer['role']
            })

    @api.one
    def send_signature_accesses(self, subject=None, message=None, ignored_partners=[]):
        if len(self.request_item_ids) <= 0:
            return False

        roles = self.request_item_ids.mapped('role_id')
        for item in self.template_id.signature_item_ids:
            if not item.responsible_id:
                continue
            if item.responsible_id not in roles:
                return False

        self.request_item_ids.filtered(lambda r: not r.partner_id or r.partner_id.id not in ignored_partners).send_signature_accesses(subject, message)
        return True

    @api.one
    def send_follower_accesses(self, followers, subject=None, message=None):
        base_context = self.env.context
        template_id = self.env.ref('website_sign.follower_access_mail_template').id
        mail_template = self.env['mail.template'].browse(template_id)

        email_from_usr = self.env.user.partner_id.name
        email_from = str(self.env.user.partner_id.name) + "<" + str(self.env.user.partner_id.email) + ">"

        for follower in followers:
            template = mail_template.sudo().with_context(base_context,
                email_from_usr = email_from_usr,
                email_from = email_from,
                email_to = follower.email,
                link = "sign/document/%s/%s?pdfview" % (self.id, self.access_token),
                subject = subject or ("Signature request - " + self.reference),
                msgbody = message or ""
            )
            template.send_mail(self.id, force_send=True)
        return True

    @api.one
    def send_completed_document(self):
        if len(self.request_item_ids) <= 0:
            return False

        if not self.completed_document:
            self.generate_completed_document()

        base_context = self.env.context
        template_id = self.env.ref('website_sign.completed_signature_mail_template').id
        mail_template = self.env['mail.template'].browse(template_id)

        email_from_usr = self.env.user.partner_id.name
        email_from = str(self.env.user.partner_id.name) + "<" + str(self.env.user.partner_id.email) + ">"

        for signer in self.request_item_ids:
            if not signer.partner_id:
                continue
            template = mail_template.sudo().with_context(base_context,
                email_from_usr = email_from_usr,
                email_from = email_from,
                email_to = signer.partner_id.email,
                link = "/sign/download/%s/%s/completed" % (self.id, self.access_token)
            )
            template.send_mail(self.id, force_send=True)

        for follower in self.follower_ids:
            template = mail_template.sudo().with_context(base_context,
                email_from_usr = email_from_usr,
                email_from = email_from,
                email_to = follower.email,
                link = "/sign/download/%s/%s/completed" % (self.id, self.access_token)
            )
            template.send_mail(self.id, force_send=True)

        return True

    @api.one
    def generate_completed_document(self):
        if len(self.template_id.signature_item_ids) <= 0:
            self.completed_document = self.template_id.attachment_id.datas
            return True

        old_pdf = PdfFileReader(StringIO.StringIO(base64.b64decode(self.template_id.attachment_id.datas)))
        box = old_pdf.getPage(0).mediaBox
        width = int(box.getUpperRight_x())
        height = int(box.getUpperRight_y())
        font = "Helvetica"

        normalFontSize = height*0.015

        packet = StringIO.StringIO()
        can = canvas.Canvas(packet)
        itemsByPage = self.template_id.signature_item_ids.getByPage()
        for p in range(0, old_pdf.getNumPages()):
            if (p+1) not in itemsByPage:
                can.showPage()
                continue

            items = itemsByPage[p+1]
            for item in items:
                value = self.env['signature.item.value'].search([('signature_item_id', '=', item.id), ('signature_request_id', '=', self.id)], limit=1)
                if not value or not value.value:
                    continue

                value = value.value

                if item.type_id.type == "text":
                    can.setFont(font, int(height*item.height*0.8))
                    can.drawString(width*item.posX, height*(1-item.posY-item.height*0.9), value)

                elif item.type_id.type == "textarea":
                    can.setFont(font, int(normalFontSize*0.8))
                    lines = value.split('\n')
                    y = height*(1-item.posY)
                    for line in lines:
                        y -= normalFontSize*0.9
                        can.drawString(width*item.posX, y, line)
                        y -= normalFontSize*0.1

                elif item.type_id.type == "signature" or item.type_id.type == "initial":
                    img = base64.b64decode(value[value.find(',')+1:])
                    can.drawImage(ImageReader(StringIO.StringIO(img)), width*item.posX, height*(1-item.posY-item.height), width*item.width, height*item.height, 'auto', True) 
            
            can.showPage()

        can.save()

        item_pdf = PdfFileReader(packet)
        new_pdf = PdfFileWriter()

        for p in range(0, old_pdf.getNumPages()):
            page = old_pdf.getPage(p)
            page.mergePage(item_pdf.getPage(p))
            new_pdf.addPage(page)

        output = StringIO.StringIO()
        new_pdf.write(output)
        self.completed_document = base64.b64encode(output.getvalue())
        output.close()
        return True

    @api.multi
    def go_to_sign_document(self):
        return {
            'name': 'Document to Sign',
            'type': 'ir.actions.act_url',
            'url': '/sign/document/' + str(self[0].id) + '?pdfview',
            'target': 'self',
        }

    @api.multi
    def go_to_custom_document(self):
        return self[0].template_id.go_to_custom_template()

    @api.multi
    def get_completed_document(self):
        if not self[0].completed_document:
            self[0].generate_completed_document()

        return {
            'name': 'Signed Document',
            'type': 'ir.actions.act_url',
            'url': '/sign/download/%s/%s/completed' % (self[0].id, self[0].access_token),
            'target': 'self',
        }

    @api.multi
    def favorite_document(self):
        self[0].write({'favorited_ids': [(3 if self.env.user in self[0].favorited_ids else 4, self.env.user.id)]})

class signature_request_item(models.Model):
    _name = "signature.request.item"
    _description = "Signature Request"
    _rec_name = 'partner_id'

    partner_id = fields.Many2one('res.partner', string="Partner", ondelete='cascade')

    signature_request_id = fields.Many2one('signature.request', string="Signature Request", ondelete='cascade', required=True)
    signature = fields.Binary()
    
    signing_date = fields.Date('Signed on', readonly=True)
    state = fields.Selection([
        ("draft", "Draft"),
        ("sent", "Waiting for completion"),
        ("completed", "Completed")
    ], readonly=True, default="draft")

    @api.multi
    def _default_access_token(self):
        return str(uuid.uuid4())
    access_token = fields.Char('Security Token', required=True, default=_default_access_token, readonly=True)

    signer_email = fields.Char(related='partner_id.email')

    @api.one
    @api.depends('partner_id.name')
    def _compute_trigram(self):
        if not self.partner_id:
            self.signer_trigram = "PU"
            return
        parts = self.partner_id.name.split(' ')
        trigram = ""
        for part in parts:
            if len(part) > 0:
                trigram += part[0]
        self.signer_trigram = trigram
    signer_trigram = fields.Char(compute=_compute_trigram)

    role_id = fields.Many2one('signature.item.party', string="Role")

    latitude = fields.Float(digits=(10, 7))
    longitude = fields.Float(digits=(10, 7))

    @api.multi
    def action_draft(self):
        self.write({
            'signature': None,
            'signing_date': None,
            'access_token': self._default_access_token(),
            'state': 'draft'
            })
        for request_item in self:
            itemsToClean = request_item.signature_request_id.template_id.signature_item_ids.filtered(lambda r: r.responsible_id == request_item.role_id or not r.responsible_id)
            self.env['signature.item.value'].search([('signature_item_id', 'in', itemsToClean.mapped('id')), ('signature_request_id', '=', request_item.signature_request_id.id)]).unlink()
        self.mapped('signature_request_id')._check_after_compute()

    @api.multi
    def action_sent(self):
        self.write({'state': 'sent'})
        self.mapped('signature_request_id')._check_after_compute()

    @api.multi
    def action_completed(self):
        self.write({'signing_date': time.strftime(DEFAULT_SERVER_DATE_FORMAT), 'state': 'completed'})
        self.mapped('signature_request_id')._check_after_compute()

    @api.one
    def sign(self, signature):
        if not isinstance(signature, dict):
            self.signature = signature
        else:
            for itemId in signature:
                item_value = self.env['signature.item.value'].search([('signature_item_id', '=', int(itemId)), ('signature_request_id', '=', self.signature_request_id.id)])
                if not item_value:
                    item_value = self.env['signature.item.value'].create({'signature_item_id': int(itemId), 'signature_request_id': self.signature_request_id.id})
                item_value.value = signature[itemId]

                if item_value.signature_item_id.type_id.type == 'signature':
                    self.signature = signature[itemId][signature[itemId].find(',')+1:]

        self.action_completed()

    @api.multi
    def send_signature_accesses(self, subject=None, message=None):
        base_context = self.env.context
        template_id = self.env.ref('website_sign.signature_access_mail_template').id
        mail_template = self.env['mail.template'].browse(template_id)

        email_from_usr = self.env.user.partner_id.name
        email_from = str(self.env.user.partner_id.name) + "<" + str(self.env.user.partner_id.email) + ">"

        for signer in self:
            if not signer.partner_id:
                continue
            template = mail_template.sudo().with_context(base_context,
                email_from_usr = email_from_usr,
                email_from = email_from,
                email_to = signer.partner_id.email,
                link = "sign/document/%s/%s" % (signer.signature_request_id.id, signer.access_token),
                subject = subject or ("Signature request - " + signer.signature_request_id.reference),
                msgbody = message or ""
            )
            template.send_mail(signer.signature_request_id.id, force_send=True)
        return True
