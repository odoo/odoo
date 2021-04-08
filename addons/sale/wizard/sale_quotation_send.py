# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _
from odoo.exceptions import UserError

class SaleQuotationSend(models.TransientModel):
    _name = 'sale.quotation.send'
    _inherits = {'mail.compose.message':'composer_id'}
    _description = 'Sale Quotation Send'

    quotation_ids = fields.Many2many('sale.order', string='Quotations')
    composer_id = fields.Many2one('mail.compose.message', string='Composer', required=True, ondelete='cascade')
    template_id = fields.Many2one(
        'mail.template', 'Use template', index=True,
        domain="[('model', '=', 'account.move')]"
    ) # TODO : change the template, this on is for invoices


    @api.model
    def default_get(self, fields):
        res = super(SaleQuotationSend, self).default_get(fields)
        res_ids = self._context.get('active_ids')

        quotation = self.env['sale.order'].browse(res_ids).filtered(lambda selected: selected.state == "draft'")
        if not quotation:
            raise UserError(_("You should select at least one quotation."))

        composer = self.env['mail.compose.message'].create({
            'composition_mode': 'comment' if len(res_ids) == 1 else 'mass_mail',
        })
        res.update({
            'quotation_ids': res_ids,
            'composer_id': composer.id,
        })
        return res

    @api.onchange('quotation_ids')
    def _compute_composition_mode(self):
        for wizard in self:
            wizard.composer_id.composition_mode = 'comment' if len(wizard.invoice_ids) == 1 else 'mass_mail'

    @api.onchange('template_id')
    def onchange_template_id(self):
        for wizard in self:
            if wizard.composer_id:
                wizard.composer_id.template_id = wizard.template_id.id
                wizard._compute_composition_mode()
                wizard.composer_id.onchange_template_id_wrapper()

    def _send_email(self):
        # with_context : we don't want to reimport the file we just exported.
        self.composer_id.with_context(mail_notify_author=self.env.user.partner_id in self.composer_id.partner_ids).send_mail()
        if self.env.context.get('mark_invoice_as_sent'):
            #Salesman send posted invoice, without the right to write
            #but they should have the right to change this flag
            self.mapped('invoice_ids').sudo().write({'is_move_sent': True})
