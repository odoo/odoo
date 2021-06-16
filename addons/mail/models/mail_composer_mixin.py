# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, tools, _


class MailComposerMixin(models.AbstractModel):
    """ Mixin used to edit and render some fields used when sending emails or
    notifications based on a mail template.

    Main current purpose is to hide details related to subject and body computation
    and rendering based on a mail.template. It also give the base tools to control
    who is allowed to edit body, notably when dealing with templating language
    like inline_template or qweb.

    It is meant to evolve in a near future with upcoming support of qweb and fine
    grain control of rendering access.
    """
    _name = 'mail.composer.mixin'
    _inherit = 'mail.render.mixin'
    _description = 'Mail Composer Mixin'

    # Content
    subject = fields.Char('Subject', compute='_compute_subject', readonly=False, store=True)
    body = fields.Html('Contents', compute='_compute_body', render_engine='qweb', store=True, readonly=False, sanitize=False)
    template_id = fields.Many2one('mail.template', 'Mail Template', domain="[('model', '=', render_model)]")
    # Access
    is_mail_template_editor = fields.Boolean('Is Editor', compute='_compute_is_mail_template_editor')
    can_edit_body = fields.Boolean('Can Edit Body', compute='_compute_can_edit_body')

    @api.depends('template_id')
    def _compute_subject(self):
        for composer_mixin in self:
            if composer_mixin.template_id:
                composer_mixin.subject = composer_mixin.template_id.subject
            elif not composer_mixin.subject:
                composer_mixin.subject = False

    @api.depends('template_id')
    def _compute_body(self):
        for composer_mixin in self:
            if composer_mixin.template_id:
                composer_mixin.body = composer_mixin.template_id.body_html
            elif not composer_mixin.body:
                composer_mixin.body = False

    @api.depends_context('uid')
    def _compute_is_mail_template_editor(self):
        is_mail_template_editor = self.env.is_admin() or self.env.user.has_group('mail.group_mail_template_editor')
        for record in self:
            record.is_mail_template_editor = is_mail_template_editor

    @api.depends('template_id', 'is_mail_template_editor')
    def _compute_can_edit_body(self):
        for record in self:
            record.can_edit_body = (
                record.is_mail_template_editor
                or not record.template_id
            )

    def _render_field(self, field, *args, **kwargs):
        """Render the given field on the given records.
        This method bypass the rights when needed to
        be able to render the template values in mass mode.
        """
        if field not in self._fields:
            raise ValueError(_("The field %s does not exist on the model %s", field, self._name))

        composer_value = self[field]

        if (
            not self.template_id
            or self.is_mail_template_editor
        ):
            # Do not need to bypass the verification
            return super(MailComposerMixin, self)._render_field(field, *args, **kwargs)

        template_field = 'body_html' if field == 'body' else field
        assert template_field in self.template_id._fields
        template_value = self.template_id[template_field]

        if field == 'body':
            sanitized_template_value = tools.html_sanitize(template_value)
            if not self.can_edit_body or composer_value in (sanitized_template_value, template_value):
                # Take the previous body which we can trust without HTML editor reformatting
                self.body = self.template_id.body_html
                return super(MailComposerMixin, self.sudo())._render_field(field, *args, **kwargs)

        elif composer_value == template_value:
            # The value is the same as the mail template so we trust it
            return super(MailComposerMixin, self.sudo())._render_field(field, *args, **kwargs)

        return super(MailComposerMixin, self)._render_field(field, *args, **kwargs)
