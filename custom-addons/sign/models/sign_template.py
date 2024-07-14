# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import re
import base64
import io

from PyPDF2 import PdfFileReader
from collections import defaultdict
from random import randint

from odoo import api, fields, models, Command, _
from odoo.exceptions import UserError, AccessError, ValidationError
from odoo.tools import pdf


class SignTemplate(models.Model):
    _name = "sign.template"
    _description = "Signature Template"

    def _default_favorited_ids(self):
        return [(4, self.env.user.id)]

    attachment_id = fields.Many2one('ir.attachment', string="Attachment", required=True, ondelete='cascade')
    name = fields.Char(related='attachment_id.name', readonly=False, store=True)
    num_pages = fields.Integer('Number of pages', compute="_compute_num_pages", readonly=True, store=True)
    datas = fields.Binary(related='attachment_id.datas')
    sign_item_ids = fields.One2many('sign.item', 'template_id', string="Signature Items", copy=True)
    responsible_count = fields.Integer(compute='_compute_responsible_count', string="Responsible Count")

    active = fields.Boolean(default=True, string="Active")
    favorited_ids = fields.Many2many('res.users', string="Favorited Users", relation="sign_template_favorited_users_rel", default=_default_favorited_ids)
    user_id = fields.Many2one('res.users', string="Responsible", default=lambda self: self.env.user)

    sign_request_ids = fields.One2many('sign.request', 'template_id', string="Signature Requests")

    tag_ids = fields.Many2many('sign.template.tag', string='Tags')
    color = fields.Integer()
    redirect_url = fields.Char(string="Redirect Link", default="",
        help="Optional link for redirection after signature")
    redirect_url_text = fields.Char(string="Link Label", default="Open Link", translate=True,
        help="Optional text to display on the button link")
    signed_count = fields.Integer(compute='_compute_signed_in_progress_template')
    in_progress_count = fields.Integer(compute='_compute_signed_in_progress_template')

    authorized_ids = fields.Many2many('res.users', string="Authorized Users", relation="sign_template_authorized_users_rel", default=_default_favorited_ids)
    group_ids = fields.Many2many("res.groups", string="Authorized Groups")
    has_sign_requests = fields.Boolean(compute="_compute_has_sign_requests", compute_sudo=True, store=True)

    is_sharing = fields.Boolean(compute='_compute_is_sharing', help='Checked if this template has created a shared document for you')

    @api.model
    def _name_search(self, name, domain=None, operator='ilike', limit=None, order=None):
        if not order:
            return super()._name_search(name, domain, operator, limit, order)
        # Display favorite templates first
        template_ids = super()._name_search(name, domain, operator, None, order)
        templates = self.browse(template_ids)
        templates = templates.sorted(key=lambda t: self.env.user in t.favorited_ids, reverse=True)
        return templates[:limit].ids

    @api.depends('attachment_id.datas')
    def _compute_num_pages(self):
        for record in self:
            try:
                record.num_pages = self._get_pdf_number_of_pages(base64.b64decode(record.attachment_id.datas))
            except Exception:
                record.num_pages = 0

    @api.depends('sign_item_ids.responsible_id')
    def _compute_responsible_count(self):
        for template in self:
            template.responsible_count = len(template.sign_item_ids.mapped('responsible_id'))

    @api.depends('sign_request_ids')
    def _compute_has_sign_requests(self):
        for template in self:
            template.has_sign_requests = bool(template.with_context(active_test=False).sign_request_ids)

    def _compute_signed_in_progress_template(self):
        sign_requests = self.env['sign.request']._read_group([('state', '!=', 'canceled')], ['state', 'template_id'], ['__count'])
        signed_request_dict = {template.id: count for state, template, count in sign_requests if state == 'signed'}
        in_progress_request_dict = {template.id: count for state, template, count in sign_requests if state == 'sent'}
        for template in self:
            template.signed_count = signed_request_dict.get(template.id, 0)
            template.in_progress_count = in_progress_request_dict.get(template.id, 0)

    @api.depends_context('uid')
    def _compute_is_sharing(self):
        sign_template_sharing_ids = set(self.env['sign.request'].search([
            ('state', '=', 'shared'), ('create_uid', '=', self.env.user.id), ('template_id', 'in', self.ids)
        ]).template_id.ids)
        for template in self:
            template.is_sharing = template.id in sign_template_sharing_ids

    @api.model
    def get_empty_list_help(self, help_message):
        if not self.env.ref('sign.template_sign_tour', raise_if_not_found=False):
            return '<p class="o_view_nocontent_smiling_face">%s</p>' % _('Upload a PDF')
        return super().get_empty_list_help(help_message)

    @api.model_create_multi
    def create(self, vals_list):
        # Sometimes the attachment is not already created in database when the sign template create method is called
        attachment_vals = [{'name': val['name'], 'datas': val.pop('datas')} for val in vals_list if not val.get('attachment_id') and val.get('datas')]
        attachments_iter = iter(self.env['ir.attachment'].create(attachment_vals))
        for val in vals_list:
            if not val.get('attachment_id', True):
                try:
                    val['attachment_id'] = next(attachments_iter).id
                except StopIteration:
                    raise UserError(_('No attachment was provided'))
        attachments = self.env['ir.attachment'].browse([vals.get('attachment_id') for vals in vals_list if vals.get('attachment_id')])
        for attachment in attachments:
            self._check_pdf_data_validity(attachment.datas)
        # copy the attachment if it has been attached to a record
        for vals, attachment in zip(vals_list, attachments):
            if attachment.res_model or attachment.res_id:
                vals['attachment_id'] = attachment.copy().id
            else:
                attachment.res_model = self._name
        templates = super().create(vals_list)
        for template, attachment in zip(templates, templates.attachment_id):
            attachment.write({
                'res_model': self._name,
                'res_id': template.id
            })
        templates.attachment_id.check('read')
        return templates

    def write(self, vals):
        res = super().write(vals)
        if 'attachment_id' in vals:
            self.attachment_id.check('read')
        return res

    def copy(self, default=None):
        self.ensure_one()
        default = default or {}
        default['name'] = default.get('name', self._get_copy_name(self.name))
        new_template = super().copy(default)
        for sign_item in new_template.sign_item_ids:
            if sign_item.type_id.item_type == 'selection':
                archived_options = sign_item.option_ids.filtered(lambda option: not option.available).ids
                if archived_options:
                    sign_item.option_ids = [Command.unlink(option) for option in archived_options]
        return new_template

    @api.model
    def create_with_attachment_data(self, name, data, active=True):
        try:
            attachment = self.env['ir.attachment'].create({'name': name, 'datas': data})
            return self.create({'attachment_id': attachment.id, 'active': active}).id
        except UserError:
            return 0

    @api.model
    def _get_pdf_number_of_pages(self, pdf_data):
        file_pdf = PdfFileReader(io.BytesIO(pdf_data), strict=False, overwriteWarnings=False)
        return file_pdf.getNumPages()

    def go_to_custom_template(self, sign_directly_without_mail=False):
        self.ensure_one()
        return {
            'name': "Template \"%(name)s\"" % {'name': self.attachment_id.name},
            'type': 'ir.actions.client',
            'tag': 'sign.Template',
            'params': {
                'id': self.id,
                'sign_directly_without_mail': sign_directly_without_mail,
            },
        }

    def _check_send_ready(self):
        if any(item.type_id.item_type == 'selection' and not item.option_ids for item in self.sign_item_ids):
            raise UserError(_("One or more selection items have no associated options"))

    def toggle_favorited(self):
        self.ensure_one()
        self.write({'favorited_ids': [(3 if self.env.user in self[0].favorited_ids else 4, self.env.user.id)]})

    @api.ondelete(at_uninstall=False)
    def _unlink_except_existing_signature(self):
        if self.filtered(lambda template: template.has_sign_requests):
            raise UserError(_(
                "You can't delete a template for which signature requests "
                "exist but you can archive it instead."))

    @api.model
    def _check_pdf_data_validity(self, datas):
        try:
            self._get_pdf_number_of_pages(base64.b64decode(datas))
        except Exception as e:
            raise UserError(_("One uploaded file cannot be read. Is it a valid PDF?"))

    def update_from_pdfviewer(self, sign_items=None, deleted_sign_item_ids=None, name=None):
        """ Update a sign.template from the pdfviewer
        :param dict sign_items: {id (str): values (dict)}
            id: positive: sign.item's id in database (the sign item is already in the database and should be update)
                negative: negative random itemId(transaction_id) in pdfviewer (the sign item is new created in the pdfviewer and should be created in database)
            values: values to update/create
        :param list(str) deleted_sign_item_ids: list of ids of deleted sign items. These deleted ids may be
            positive: the sign item exists in the database
            negative: the sign item is new created in pdfviewer but removed before a successful transaction
        :return: dict new_id_to_item_id_map: {negative itemId(transaction_id) in pdfviewer (str): positive id in database (int)}
        """
        self.ensure_one()
        if self.has_sign_requests:
            return False
        if sign_items is None:
            sign_items = {}

        # The name may be "" and None here. And the attachment_id.name is forcely written here to retry the method and
        # avoid recreating new sign items when two RPCs arrive at the same time
        self.attachment_id.name = name if name else self.attachment_id.name

        # update new_sign_items to avoid recreating sign items
        new_sign_items = dict(sign_items)
        sign_items_exist = self.sign_item_ids.filtered(lambda r: str(r.transaction_id) in sign_items)
        for sign_item in sign_items_exist:
            new_sign_items[str(sign_item.id)] = new_sign_items.pop(str(sign_item.transaction_id))
        new_id_to_item_id_map = {str(sign_item.transaction_id): sign_item.id for sign_item in sign_items_exist}

        # unlink sign items
        deleted_sign_item_ids = set() if deleted_sign_item_ids is None else set(deleted_sign_item_ids)
        self.sign_item_ids.filtered(lambda r: r.id in deleted_sign_item_ids or (r.transaction_id in deleted_sign_item_ids)).unlink()

        # update existing sign items
        for item in self.sign_item_ids.filtered(lambda r: str(r.id) in new_sign_items):
            str_item_id = str(item.id)
            if 'option_ids' in new_sign_items.get(str_item_id):
                new_option_ids = list(map(int, new_sign_items[str_item_id]['option_ids']))
                new_sign_items[str_item_id]['option_ids'] = [[6, 0, new_option_ids]]
            item.write(new_sign_items.pop(str_item_id))

        # create new sign items
        new_values_list = []
        for key, values in new_sign_items.items():
            if int(key) < 0:
                values['template_id'] = self.id
                new_values_list.append(values)
        new_id_to_item_id_map.update(zip(new_sign_items.keys(), self.env['sign.item'].create(new_values_list).ids))

        return new_id_to_item_id_map

    @api.model
    def _get_copy_name(self, name):
        regex = re.compile(r'(.*?)((?:\(\d+\))?)((?:\.pdf)?)$')
        match = regex.search(name)
        name_doc = match.group(1)
        name_ver = match.group(2)
        name_ext = match.group(3)
        version = int(name_ver[1:-1]) + 1 if name_ver else 2
        return f"{name_doc}({version}){name_ext}"

    @api.model
    def rotate_pdf(self, template_id=None):
        template = self.browse(template_id)
        if template.has_sign_requests:
            return False

        template.datas = base64.b64encode(pdf.rotate_pdf(base64.b64decode(template.datas)))

        return True

    def open_requests(self):
        return {
            "type": "ir.actions.act_window",
            "name": _("Sign requests"),
            "res_model": "sign.request",
            "res_id": self.id,
            "domain": [["template_id", "in", self.ids]],
            "views": [[False, 'kanban'], [False, "form"]],
            "context": {'search_default_signed': True}
        }

    def open_shared_sign_request(self):
        self.ensure_one()
        shared_sign_request = self.sign_request_ids.filtered(lambda sr: sr.state == 'shared' and sr.create_uid == self.env.user)
        if not shared_sign_request:
            if len(self.sign_item_ids.mapped('responsible_id')) > 1:
                raise ValidationError(_("You cannot share this document by link, because it has fields to be filled by different roles. Use Send button instead."))
            shared_sign_request = self.env['sign.request'].with_context(no_sign_mail=True).create({
                'template_id': self.id,
                'request_item_ids': [Command.create({'role_id': self.sign_item_ids.responsible_id.id or self.env.ref('sign.sign_item_role_default').id})],
                'reference': "%s-%s" % (self.name, _("Shared")),
                'state': 'shared',
            })
        return {
            "name": _("Share Document by Link"),
            'type': 'ir.actions.act_window',
            "res_model": "sign.request",
            "res_id": shared_sign_request.id,
            "target": "new",
            'views': [[self.env.ref("sign.sign_request_share_view_form").id, 'form']],
        }

    def stop_sharing(self):
        self.ensure_one()
        return self.sign_request_ids.filtered(lambda sr: sr.state == 'shared' and sr.create_uid == self.env.user).unlink()

    def _copy_sign_items_to(self, new_template):
        """ copy all sign items of the self template to the new_template """
        self.ensure_one()
        if new_template.has_sign_requests:
            raise UserError(_("Somebody is already filling a document which uses this template"))
        item_id_map = {}
        for sign_item in self.sign_item_ids:
            new_sign_item = sign_item.copy({'template_id': new_template.id})
            item_id_map[str(sign_item.id)] = str(new_sign_item.id)
        return item_id_map

    def _get_sign_items_by_page(self):
        self.ensure_one()
        items = defaultdict(lambda: self.env['sign.item'])
        for item in self.sign_item_ids:
            items[item.page] += item
        return items

    def trigger_template_tour(self):
        template = self.env.ref('sign.template_sign_tour')
        if template.has_sign_requests:
            template = template.copy({
                'favorited_ids': [Command.link(self.env.user.id)],
                'active': False
            })
        return {
            'type': 'ir.actions.client',
            'tag': 'sign.Template',
            'name': template.name,
            'params': {
                'sign_edit_call': 'sign_send_request',
                'id': template.id,
                'sign_directly_without_mail': False
            }
        }


class SignTemplateTag(models.Model):

    _name = "sign.template.tag"
    _description = "Sign Template Tag"
    _order = "name"

    def _get_default_color(self):
        return randint(1, 11)

    name = fields.Char('Tag Name', required=True, translate=True)
    color = fields.Integer('Color Index', default=_get_default_color)

    _sql_constraints = [
        ('name_uniq', 'unique (name)', "Tag name already exists!"),
    ]


class SignItemSelectionOption(models.Model):
    _name = "sign.item.option"
    _description = "Option of a selection Field"
    _rec_name = "value"

    value = fields.Text(string="Option", readonly=True)
    available = fields.Boolean(string="Available in new templates", default=True)

    _sql_constraints = [
        ('value_uniq', 'unique (value)', "Value already exists!"),
    ]

    @api.model
    def name_create(self, name):
        existing_option = self.search([('value', '=ilike', name.strip())], limit=1)
        if existing_option:
            existing_option.available = True
            return existing_option.id, existing_option.display_name
        return super().name_create(name)


class SignItem(models.Model):
    _name = "sign.item"
    _description = "Fields to be sign on Document"
    _order = "page asc, posY asc, posX asc"
    _rec_name = 'template_id'

    template_id = fields.Many2one('sign.template', string="Document Template", required=True, ondelete='cascade')

    type_id = fields.Many2one('sign.item.type', string="Type", required=True, ondelete='restrict')

    required = fields.Boolean(default=True)
    responsible_id = fields.Many2one("sign.item.role", string="Responsible", ondelete="restrict")

    option_ids = fields.Many2many("sign.item.option", string="Selection options")

    name = fields.Char(string="Field Name", default=lambda self: self.type_id.placeholder)
    page = fields.Integer(string="Document Page", required=True, default=1)
    posX = fields.Float(digits=(4, 3), string="Position X", required=True)
    posY = fields.Float(digits=(4, 3), string="Position Y", required=True)
    width = fields.Float(digits=(4, 3), required=True)
    height = fields.Float(digits=(4, 3), required=True)
    alignment = fields.Char(default="center", required=True)

    transaction_id = fields.Integer(copy=False)


class SignItemType(models.Model):
    _name = "sign.item.type"
    _description = "Signature Item Type"

    name = fields.Char(string="Field Name", required=True, translate=True)
    item_type = fields.Selection([
        ('signature', "Signature"),
        ('initial', "Initial"),
        ('text', "Text"),
        ('textarea', "Multiline Text"),
        ('checkbox', "Checkbox"),
        ('selection', "Selection"),
    ], required=True, string='Type', default='text')

    tip = fields.Char(required=True, default="fill in", help="Hint displayed in the signing hint", translate=True)
    placeholder = fields.Char(translate=True)

    default_width = fields.Float(string="Default Width", digits=(4, 3), required=True, default=0.150)
    default_height = fields.Float(string="Default Height", digits=(4, 3), required=True, default=0.015)
    auto_field = fields.Char(string="Auto-fill Partner Field", groups='base.group_system',
        help="Technical name of the field on the partner model to auto-complete this signature field at the time of signature.")

    @api.constrains('auto_field')
    def _check_auto_field_exists(self):
        partner = self.env['res.partner'].browse(self.env.user.partner_id.id)
        for sign_type in self:
            if sign_type.auto_field:
                try:
                    if isinstance(partner.mapped(sign_type.auto_field), models.BaseModel):
                        raise AttributeError
                except (KeyError, AttributeError):
                    raise ValidationError(_("Malformed expression: %(exp)s", exp=sign_type.auto_field))


class SignItemParty(models.Model):
    _name = "sign.item.role"
    _description = "Signature Item Party"
    _rec_name = "name"
    _order = "sequence, id"

    name = fields.Char(required=True, translate=True)
    color = fields.Integer()
    default = fields.Boolean(required=True, default=False)
    sequence = fields.Integer(string="Default order", default=10)

    auth_method = fields.Selection(string="Extra Authentication Step", selection=[
        ('sms', 'Unique Code via SMS')
    ], default=False, help="Force the signatory to identify using a second authentication method")

    change_authorized = fields.Boolean('Change Authorized', help="If checked, recipient of a document with this role can be changed after having sent the request. Useful to replace a signatory who is out of office, etc.")

    _sql_constraints = [
        ('name_uniq', 'unique (name)', "Name already exists!"),
    ]

    def write(self, vals):
        vals.pop('default', None)
        return super().write(vals)

    @api.ondelete(at_uninstall=False)
    def _unlink_role(self):
        for role in self:
            if role.default:
                raise AccessError(_("The role %s is required by the Sign application and cannot be deleted.", role.name))
