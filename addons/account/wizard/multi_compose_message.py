# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models


class MultiComposer(models.TransientModel):

    _name = 'multi.compose.message'
    _inherit = 'mail.compose.message'

    company_id = fields.Many2one('res.company', string='Company', required=True, readonly=True,
        default=lambda self: self.env.user.company_id.id)
    is_email = fields.Boolean('Email', default=lambda self: self.env.user.company_id.is_email)
    is_print = fields.Boolean('Print', default=lambda self: self.env.user.company_id.is_print)
    printed = fields.Boolean('Is Printed', default=False)
    partner_ids = fields.Many2many(
        'res.partner', 'account_compose_message_res_partner_rel',
        'wizard_id', 'partner_id', 'Additional Contacts')
    attachment_ids = fields.Many2many(
        'ir.attachment', 'account_compose_message_ir_attachments_rel',
        'wizard_id', 'attachment_id', 'Attachments')
    print_attachment_id = fields.Many2one('ir.attachment', string='Print Attachment')

    @api.multi
    def _update_company(self):
        for rec in self:
            values = {}
            for field in ['is_print', 'is_email']:
                if rec.company_id[field] != rec[field]:
                    values.update({field: rec[field]})
            if values:
                rec.company_id.write(values)

    @api.multi
    def write(self, vals):
        res = super(MultiComposer, self).write(vals)
        self._update_company()
        return res

    @api.multi
    @api.onchange('template_id')
    def onchange_template_id_wrapper(self):
        self.ensure_one()
        super(MultiComposer,self).onchange_template_id_wrapper()
        self.print_attachment_id = self.attachment_ids[:1]

    def _send_email(self):
        if self.is_email:
            self.send_mail()

    @api.multi
    def _print_document(self):
        """ to override for each type of models that will use this composer."""
        self.ensure_one()
        action = {
            'type': 'ir.actions.act_url',
            'url': '/web/content/%s?download=true' % (self.print_attachment_id.id),
            'target': 'new',
        }
        self.printed = True
        return action

    @api.multi
    def send_and_print_action(self):
        self.ensure_one()
        self._send_email()
        return self._print_document()

    @api.multi
    def send_action(self):
        for wizard in self:
            wizard._send_email()
        return {'type': 'ir.actions.act_window_close'}

    @api.multi
    def print_action(self):
        self.ensure_one()
        return self._print_document()
