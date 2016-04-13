# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, models


class AccountInvoice(models.Model):
    _inherit = 'account.invoice'

    @api.multi
    def invoice_validate(self):
        # fetch the partner's id and subscribe the partner to the invoice
        for invoice in self:
            if invoice.partner_id not in invoice.message_partner_ids:
                invoice.message_subscribe([invoice.partner_id.id])
        return super(AccountInvoice, self).invoice_validate()

    @api.multi
    def get_signup_url(self):
        self.ensure_one()
        return self.partner_id.with_context(signup_valid=True)._get_signup_url_for_action(
            action='/mail/view',
            model=self._name,
            res_id=self.id)[self.partner_id.id]

    @api.multi
    def get_formview_action(self):
        # NOTE : if this method is call as sudo, the only to determine if the user is portal is to check the uid from context
        # This was introduced with https://github.com/odoo/odoo/commit/f5fedbcb18a57ee9aeab952f3ff95f692f7a863c, and should be better fixed.
        uid = self.env.context.get('uid', self.env.user.id)
        if self.env['res.users'].sudo().browse(uid).share:
            return self.env['ir.actions.act_window'].for_xml_id('portal_sale', 'portal_action_invoices')
        return super(AccountInvoice, self).get_formview_action()
