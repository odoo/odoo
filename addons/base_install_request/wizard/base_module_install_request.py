# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _
from odoo.exceptions import UserError
from odoo.tools.mail import is_html_empty


class BaseModuleInstallRequest(models.TransientModel):
    _name = 'base.module.install.request'
    _description = "Module Activation Request"
    _rec_name = "module_id"

    module_id = fields.Many2one(
        'ir.module.module', string="Module", required=True,
        domain=[('state', '=', "uninstalled")],
        ondelete='cascade', readonly=True,
    )
    user_id = fields.Many2one('res.users', default=lambda self: self.env.user, required=True)
    user_ids = fields.Many2many('res.users', string="Send to:", compute='_compute_user_ids')
    body_html = fields.Html('Body')

    @api.depends('module_id')
    def _compute_user_ids(self):
        users = self.env.ref('base.group_system').all_user_ids
        self.user_ids = [(6, 0, users.ids)]

    def action_send_request(self):
        mail_template = self.env.context.get('request_template_id', 'base_install_request.mail_installation_request_template')
        menu_id = self.env.ref('base.menu_apps').id
        for user in self.user_ids:
            mail_content_html = self.env['ir.qweb']._render(mail_template,
                {
                    'body_html': self.body_html,
                    'menu_id': menu_id,
                    'module_id': self.module_id,
                    'partner': user.partner_id,
                    'request': self,
                    'show_body': not is_html_empty(self.body_html),
                }
            )
            mail_body_html = self.env['mail.render.mixin']._render_encapsulate(
                'mail.mail_notification_light',
                mail_content_html,
                add_context={
                    'model_description': _('Module Activation Request for "%s"', self.module_id.shortdesc),
                })

            mail_values = {
                'subject': _('Module Activation Request for "%s"', self.module_id.shortdesc),
                'body_html': mail_body_html,
                'email_from': self.user_id.email_formatted or self.env.user.email_formatted,
                'recipient_ids': [(4, user.partner_id.id)],
                'auto_delete': True,
            }

            mail = self.env['mail.mail'].sudo().create(mail_values)
            mail.send()

        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'type': 'success',
                'message': _('Request sent'),
                'next': {'type': 'ir.actions.act_window_close'},
            }
        }


class BaseModuleInstallReview(models.TransientModel):
    _name = 'base.module.install.review'
    _description = "Module Activation Review"
    _rec_name = "module_id"

    module_id = fields.Many2one(
        'ir.module.module', string="Module", required=True,
        domain=[('state', '=', "uninstalled")],
        ondelete='cascade', readonly=True,
    )
    module_ids = fields.Many2many(
        'ir.module.module', string="Depending Apps", compute='_compute_modules_description')
    modules_description = fields.Html(compute='_compute_modules_description')

    @api.depends('module_id')
    def _compute_modules_description(self):
        for wizard in self:
            apps = wizard._get_depending_apps(wizard.module_id)
            wizard.module_ids = [(6, 0, apps.ids)]
            wizard.modules_description = self.env["ir.qweb"]._render(
                "base_install_request.base_module_install_review_description", {'apps': apps})

    @api.model
    def _get_depending_apps(self, module):
        if not module:
            raise UserError(_('No module selected.'))
        if module.state == "installed":
            raise UserError(_('The module is already installed.'))
        deps = module.upstream_dependencies()
        apps = module | deps.filtered(lambda d: d.application)
        for dep in deps:
            apps |= dep.upstream_dependencies()
        return apps

    def action_install_module(self):
        self.ensure_one()
        self.module_id.button_immediate_install()
        return {
            'type': 'ir.actions.client',
            'tag': 'home',
        }
