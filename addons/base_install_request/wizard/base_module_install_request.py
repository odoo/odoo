# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _
from odoo.exceptions import UserError


class BaseModuleInstallRequest(models.TransientModel):
    _name = "base.module.install.request"
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
        users = self.env.ref('base.group_system').users
        self.user_ids = [(6, 0, users.ids)]

    def action_send_request(self):
        mail_template = self.env.ref('base_install_request.mail_template_base_install_request')
        menu_id = self.env.ref('base.menu_apps').id
        for user in self.user_ids:
            render_ctx = dict(self.env.context, partner=user.partner_id, menu_id=menu_id)
            mail_template.with_context(render_ctx).send_mail(
                self.id,
                force_send=True,
                email_layout_xmlid='mail.mail_notification_light')
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'type': 'success',
                'message': _('Your request has been successfully sent'),
                'next': {'type': 'ir.actions.act_window_close'},
            }
        }


class BaseModuleInstallReview(models.TransientModel):
    _name = "base.module.install.review"
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
