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
    _inherit = ['mail.render.mixin']
    _description = 'Mail Composer Mixin'

    # Content
    subject = fields.Char('Subject', compute='_compute_subject', readonly=False, store=True, compute_sudo=False)
    body = fields.Html(
        'Contents', compute='_compute_body', readonly=False, store=True, compute_sudo=False,
        render_engine='qweb', render_options={'post_process': True}, sanitize='email_outgoing')
    body_has_template_value = fields.Boolean(
        'Body content is the same as the template',
        compute='_compute_body_has_template_value',
    )
    template_id = fields.Many2one('mail.template', 'Mail Template', domain="[('model', '=', render_model)]")
    # Language: override mail.render.mixin field, copy template value
    lang = fields.Char(compute='_compute_lang', precompute=True, readonly=False, store=True, compute_sudo=False)
    # Access
    is_mail_template_editor = fields.Boolean('Is Editor', compute='_compute_is_mail_template_editor')
    can_edit_body = fields.Boolean('Can Edit Body', compute='_compute_can_edit_body')

    @api.depends('template_id')
    def _compute_subject(self):
        """ Computation is coming either from template, either reset. When
        having a template with a value set, copy it. When removing the
        template, reset it. """
        for composer_mixin in self:
            if composer_mixin.template_id.subject:
                composer_mixin.subject = composer_mixin.template_id.subject
            elif not composer_mixin.template_id:
                composer_mixin.subject = False

    @api.depends('template_id')
    def _compute_body(self):
        """ Computation is coming either from template, either reset. When
        having a template with a value set, copy it. When removing the
        template, reset it. """
        for composer_mixin in self:
            if not tools.is_html_empty(composer_mixin.template_id.body_html):
                composer_mixin.body = composer_mixin.template_id.body_html
            elif not composer_mixin.template_id:
                composer_mixin.body = False

    @api.depends('body', 'template_id')
    def _compute_body_has_template_value(self):
        """ Computes if the current body is the same as the one from template.
        Both real and sanitized values are considered, to avoid editor issues
        as much as possible. """
        for composer_mixin in self:
            if not tools.is_html_empty(composer_mixin.body) and composer_mixin.template_id:
                template_value = composer_mixin.template_id.body_html
                sanitized_template_value = tools.html_sanitize(template_value)
                composer_mixin.body_has_template_value = composer_mixin.body in (template_value, sanitized_template_value)
            else:
                composer_mixin.body_has_template_value = False

    @api.depends('template_id')
    def _compute_lang(self):
        """ Computation is coming either from template, either reset. When
        having a template with a value set, copy it. When removing the
        template, reset it. """
        for composer_mixin in self:
            if composer_mixin.template_id.lang:
                composer_mixin.lang = composer_mixin.template_id.lang
            elif not composer_mixin.template_id:
                composer_mixin.lang = False

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

    def _render_lang(self, *args, **kwargs):
        """ Given some record ids, return the lang for each record based on
        lang field of template or through specific context-based key.
        This method enters sudo mode to allow qweb rendering (which
        is otherwise reserved for the 'mail template editor' group')
        if we consider it safe. Safe means content comes from the template
        which is a validated master data. As a summary the heuristic is :

          * if no template, do not bypass the check;
          * if record lang and template lang are the same, bypass the check;
        """

        if not self.template_id:
            # Do not need to bypass the verification
            return super()._render_lang(*args, **kwargs)

        composer_value = self.lang
        template_value = self.template_id.lang

        call_sudo = False
        if (not self.is_mail_template_editor and composer_value == template_value):
            call_sudo = True

        record = self.sudo() if call_sudo else self
        return super(MailComposerMixin, record)._render_lang(*args, **kwargs)

    def _render_field(self, field, *args, **kwargs):
        """ Render the given field on the given records. This method enters
        sudo mode to allow qweb rendering (which is otherwise reserved for
        the 'mail template editor' group') if we consider it safe. Safe
        means content comes from the template which is a validated master
        data. As a summary the heuristic is :

          * if no template, do not bypass the check;
          * if current user is a template editor, do not bypass the check;
          * if record value and template value are the same (or equals the
            sanitized value in case of an HTML field), bypass the check;
          * for body: if current user cannot edit it, force template value back
            then bypass the check;

        Also provide support to fetch translations on the remote template.
        Indeed translations are often done on the master template, not on the
        specific composer itself. In that case we need to work on template
        value when it has not been modified in the composer. """
        if field not in self:
            raise ValueError(
                _('Rendering of %(field_name)s is not possible as not defined on template.',
                  field_name=field
                 )
            )

        if not self.template_id:
            # Do not need to bypass the verification
            return super()._render_field(field, *args, **kwargs)

        # template-based access check + translation check
        template_field = {
            'body': 'body_html',
        }.get(field, field)
        if template_field not in self.template_id:
            raise ValueError(
                _('Rendering of %(field_name)s is not possible as no counterpart on template.',
                  field_name=field
                 )
            )

        composer_value = self[field]
        template_value = self.template_id[template_field]
        translation_asked = kwargs.get('compute_lang') or kwargs.get('set_lang')
        equality = self.body_has_template_value if field == 'body' else composer_value == template_value

        call_sudo = False
        if (not self.is_mail_template_editor and field == 'body' and
            (not self.can_edit_body or self.body_has_template_value)):
            call_sudo = True
            # take the previous body which we can trust without HTML editor reformatting
            self.body = self.template_id.body_html
        if (not self.is_mail_template_editor and field != 'body' and
              composer_value == template_value):
            call_sudo = True

        if translation_asked and equality:
            template = self.template_id.sudo() if call_sudo else self.template_id
            return template._render_field(
                template_field, *args, **kwargs,
            )

        record = self.sudo() if call_sudo else self
        return super(MailComposerMixin, record)._render_field(field, *args, **kwargs)
