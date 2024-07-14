# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import re

from markupsafe import Markup

from odoo import SUPERUSER_ID, api, fields, models, _
from odoo.tools import is_html_empty


class ProposeChange(models.TransientModel):
    _name = 'propose.change'
    _description = 'Propose a change in the production'

    IMG_REGEX = re.compile(r'(<img .*?">)')

    workorder_id = fields.Many2one(
        'mrp.workorder', 'Workorder', required=True, ondelete='cascade')
    title = fields.Char('Title')
    step_id = fields.Many2one('quality.check', 'Step to change')
    note = fields.Html('New Instruction')
    comment = fields.Char('Comment')
    picture = fields.Binary('Picture')
    change_type = fields.Selection([
        ('update_step', 'Update Current Step'),
        ('remove_step', 'Remove Current Step'),
        ('set_picture', 'Set Picture')], 'Type of Change')

    def default_get(self, fields_list):
        defaults = super().default_get(fields_list)
        if 'step_id' in defaults:
            step = self.env['quality.check'].browse(defaults.get('step_id'))
            defaults['title'] = step.title
        return defaults

    def process(self):
        for wizard in self:
            if wizard.change_type == 'update_step':
                wizard._do_update_step()
            elif wizard.change_type == 'remove_step':
                wizard._do_remove_step()
            elif wizard.change_type == 'set_picture':
                wizard._do_set_picture()

    def _workorder_name(self):
        if self.workorder_id.employee_id:
            return self.workorder_id.employee_id.name
        return self.env.user.name

    def _get_update_step_note(self, original_title=False):
        tl_text = _("New Instruction suggested by %(user_name)s", user_name=self._workorder_name())
        body = Markup("<b>%s</b>") % tl_text
        if self.note and not is_html_empty(self.note):
            body += Markup("<br/>%s") % self.note
        if self.comment:
            body += Markup("<br/><b>%s</b> %s") % (_("Reason:"), self.comment)
        if self.title and self.title != original_title:
            body += Markup("<br/><b>%s %s</b>") % (_("New Title suggested:"), self.title)
        return body

    def _do_update_step(self, notify_bom=True):
        self.ensure_one()
        existing_imgs = []
        is_blank = is_html_empty(self.note)
        if not is_html_empty(self.step_id.note) and (is_blank or re.sub(self.IMG_REGEX, '', self.note) == self.note):
            # blank suggestion or only text => keep existing images if they exist
            existing_imgs = re.findall(self.IMG_REGEX, self.step_id.note)
        if existing_imgs:
            self.step_id.note = Markup('<p>%s</p>') % Markup('<br>').join(map(Markup, existing_imgs))
            if not is_blank:
                self.step_id.note = self.note + self.step_id.note
        else:
            self.step_id.note = self.note
        if notify_bom and self.workorder_id.production_id.bom_id:
            self.env['mail.activity'].sudo().create({
                'res_model_id': self.env.ref('mrp.model_mrp_bom').id,
                'res_id': self.workorder_id.production_id.bom_id.id,
                'user_id': self.workorder_id.product_id.responsible_id.id or SUPERUSER_ID,
                'activity_type_id': self.env.ref('mail.mail_activity_data_todo').id,
                'summary': _('BoM feedback %s (%s)', self.step_id.title, self.workorder_id.production_id.name),
                'note': self._get_update_step_note(self.step_id.title),
            })
        if self.title and self.title != self.step_id.title:
            self.step_id.title = self.title

    def _get_remove_step_note(self):
        tl_text = _("%(user_name)s suggests to delete this instruction", user_name=self._workorder_name())
        body = Markup("<b>%s</b>") % tl_text
        if self.comment:
            body += Markup("<br/><b>%s</b> %s") % (_("Reason:"), self.comment)
        return body

    def _do_remove_step(self, notify_bom=True):
        self.ensure_one()
        if not self.step_id.point_id and not(self.step_id.test_type.startswith('register_')):
            # remove additionmal step
            self.step_id.workorder_id._change_quality_check('next')
            self.step_id.unlink()

        self.step_id.is_deleted = True
        bom = self.step_id.workorder_id.production_id.bom_id
        if notify_bom and bom:
            self.env['mail.activity'].sudo().create({
                'res_model_id': self.env.ref('mrp.model_mrp_bom').id,
                'res_id': bom.id,
                'user_id': self.workorder_id.product_id.responsible_id.id or SUPERUSER_ID,
                'activity_type_id': self.env.ref('mail.mail_activity_data_todo').id,
                'summary': _('BoM feedback %s (%s)', self.step_id.title, self.workorder_id.production_id.name),
                'note': self._get_remove_step_note(),
            })

    @api.model
    def image_url(self, record, field):
        """ Returns a local url that points to the image field of a given browse record. """
        return '/web/image/%s/%s/%s' % (record._name, record.id, field)

    def _get_set_picture_note(self):
        lt_text = _("%(user_name)s suggests to use this document as instruction", user_name=self._workorder_name())
        return Markup('<b>%s</b><br/><img style="max-width: 75%%" class="img-fluid" src="%s"/>')\
            % (lt_text, self.image_url(self, 'picture'))

    def _do_set_picture(self, notify_bom=True):
        self.ensure_one()
        # remove html existing images, but keep existing text
        existing_text = False
        if not is_html_empty(self.step_id.note):
            existing_text = Markup(re.sub(self.IMG_REGEX, '', self.step_id.note))
        if existing_text and not is_html_empty(existing_text):
            self.step_id.note = existing_text
            existing_text = True
        # unfortunately source_document is not a field in step_id so we have to put the image in the note to ensure it shows in the WO
        if self.step_id.point_id.source_document != 'step':
            image = Markup('<img style="max-width: 75%%" class="img-fluid" src="%s"/>') % self.image_url(self, 'picture')
            if existing_text:
                self.step_id.note += image
            else:
                self.step_id.note = image
        self.step_id.worksheet_document = self.picture
        bom = self.step_id.workorder_id.production_id.bom_id
        if notify_bom and bom:
            self.env['mail.activity'].sudo().create({
                'res_model_id': self.env.ref('mrp.model_mrp_bom').id,
                'res_id': bom.id,
                'user_id': self.workorder_id.product_id.responsible_id.id or SUPERUSER_ID,
                'activity_type_id': self.env.ref('mail.mail_activity_data_todo').id,
                'summary': _('BoM feedback %s (%s)', self.step_id.title, self.workorder_id.production_id.name),
                'note': self._get_set_picture_note(),
            })
