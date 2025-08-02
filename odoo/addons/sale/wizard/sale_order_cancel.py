# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import _, api, fields, models
from odoo.exceptions import UserError


class SaleOrderCancel(models.TransientModel):
    _name = 'sale.order.cancel'
    _inherit = 'mail.composer.mixin'
    _description = "Sales Order Cancel"

    @api.model
    def _default_author_id(self):
        return self.env.user.partner_id

    # origin
    author_id = fields.Many2one(
        'res.partner',
        string="Author",
        index=True,
        ondelete='set null',
        default=_default_author_id,
    )

    # recipients
    recipient_ids = fields.Many2many(
        'res.partner',
        string="Recipients",
        compute='_compute_recipient_ids',
        readonly=False,
    )
    order_id = fields.Many2one('sale.order', string="Sale Order", required=True, ondelete='cascade')
    display_invoice_alert = fields.Boolean(
        string="Invoice Alert",
        compute='_compute_display_invoice_alert',
        compute_sudo=True,
    )

    @api.depends('order_id')
    def _compute_recipient_ids(self):
        for wizard in self:
            wizard.recipient_ids = wizard.order_id.partner_id \
                                   | wizard.order_id.message_partner_ids \
                                   - wizard.author_id

    @api.depends('order_id')
    def _compute_display_invoice_alert(self):
        for wizard in self:
            wizard.display_invoice_alert = bool(
                wizard.order_id.invoice_ids.filtered(lambda inv: inv.state == 'draft')
            )

    @api.depends('order_id')
    def _compute_subject(self):
        for wizard_su in self.filtered('template_id'):
            wizard_su.subject = wizard_su.template_id._render_field(
                'subject',
                [wizard_su.order_id.id],
                compute_lang=True,
                options={'post_process': True},
            )[wizard_su.order_id.id]

    @api.depends('order_id')
    def _compute_body(self):
        for wizard_su in self.filtered('template_id'):
            wizard_su.body = wizard_su.template_id._render_field(
                'body_html',
                [wizard_su.order_id.id],
                compute_lang=True,
                options={'post_process': True},
            )[wizard_su.order_id.id]

    def action_send_mail_and_cancel(self):
        self.ensure_one()
        self.order_id.message_post(
            author_id=self.author_id.id,
            body=self.body,
            message_type='comment',
            email_layout_xmlid='mail.mail_notification_light',
            partner_ids=self.recipient_ids.ids,
            subject=self.subject,
        )
        return self.action_cancel()

    def action_cancel(self):
        return self.order_id.with_context(disable_cancel_warning=True).action_cancel()
