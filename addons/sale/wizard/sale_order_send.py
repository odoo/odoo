# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _
from odoo.addons.mail.wizard.mail_compose_message import _reopen
from odoo.exceptions import UserError
from odoo.tools.misc import get_lang


class SaleOrderSend(models.TransientModel):
    _name = 'sale.order.send'
    _inherits = {'mail.compose.message':'composer_id'}
    _description = 'Sale Order Send'

    is_email = fields.Boolean('Email', default=lambda self: self.env.company.order_is_email)
    sale_without_email = fields.Text(compute='_compute_sale_without_email', string='order(s) that will not be sent')
    is_print = fields.Boolean('Print', default=lambda self: self.env.company.order_is_print)
    printed = fields.Boolean('Is Printed', default=False)
    order_ids = fields.Many2many('sale.order', 'sale_order_send_rel', string='orders')
    composer_id = fields.Many2one('mail.compose.message', string='Composer', required=True, ondelete='cascade')
    template_id = fields.Many2one(
        'mail.template', 'Use template', index=True,
        domain="[('model', '=', 'sale.order')]"
        )

    @api.model
    def default_get(self, fields):
        res = super(SaleOrderSend, self).default_get(fields)
        res_ids = self._context.get('active_ids')
        composer = self.env['mail.compose.message'].create({
            'composition_mode': 'comment',
        })

        res.update({
            'order_ids': res_ids,
            'composer_id': composer.id,
        })
        return res

    @api.onchange('template_id')
    def onchange_template_id(self):
        for wizard in self:
            if wizard.composer_id:
                wizard.composer_id.template_id = wizard.template_id.id
                wizard.composer_id.onchange_template_id_wrapper()

    @api.onchange('is_email')
    def onchange_is_email(self):
        if self.is_email:
            if not self.composer_id:
                res_ids = self._context.get('active_ids')
                self.composer_id = self.env['mail.compose.message'].create({
                    'composition_mode': 'comment',
                    'template_id': self.template_id.id
                })
            self.composer_id.onchange_template_id_wrapper()

    @api.onchange('is_email')
    def _compute_sale_without_email(self):
        for wizard in self:
            if wizard.is_email and len(wizard.order_ids) > 1:
                orders = self.env['sale.order'].search([
                    ('id', 'in', self.env.context.get('active_ids')),
                    ('partner_id.email', '=', False)
                ])
                if orders:
                    wizard.sale_without_email = "%s\n%s" % (
                        _("The following order(s) will not be sent by email, because the customers don't have email address."),
                        "\n".join([i.name for i in orders])
                        )
                else:
                    wizard.sale_without_email = False
            else:
                wizard.sale_without_email = False

    def _send_email(self):
        if self.is_email:
            self.composer_id.send_mail()

    def _print_document(self):
        self.ensure_one()
        action = self.order_ids.action_sale_print()
        action.update({'close_on_report_download': True})
        return action

    def send_and_print_action(self):
        self.ensure_one()
        if self.is_email:
            self._send_email()
        if self.is_print:
            return self._print_document()
        return {'type': 'ir.actions.act_window_close'}

    def save_as_template(self):
        self.ensure_one()
        self.composer_id.save_as_template()
        action = _reopen(self, self.id, self.model, context=self._context)
        action.update({'name': _('Send Sale Order')})
        return action
