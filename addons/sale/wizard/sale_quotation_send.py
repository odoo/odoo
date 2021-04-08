# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _
from odoo.exceptions import UserError
from odoo.tools.misc import get_lang

class SaleQuotationSend(models.TransientModel):
    _name = 'sale.quotation.send'
    _inherits = {'mail.compose.message':'composer_id'}
    _description = 'Sale Quotation Send'

    quotation_ids = fields.Many2many('sale.order', 'sale_order_sale_quotation_send_rel', string='Quotations')
    quotation_without_email = fields.Text(compute='_compute_quotation_without_email', string='quotation(s) that will not be sent')
    composer_id = fields.Many2one('mail.compose.message', string='Composer', required=True, ondelete='cascade')
    template_id = fields.Many2one(
        'mail.template', 'Use template', index=True,
        domain="[('model', '=', 'account.move')]"
    ) # TODO : change the template, this on is for invoices


    @api.model
    def default_get(self, fields):
        import ipdb; ipdb.set_trace()
        res = super(SaleQuotationSend, self).default_get(fields)
        res_ids = self._context.get('active_ids')
        import ipdb; ipdb.set_trace()
        quotation = self.env['sale.order'].browse(res_ids).filtered(lambda selected: selected.state == 'draft')
        if not quotation:
            raise UserError(_('You should select at least one quotation.'))

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
            wizard.composer_id.composition_mode = 'comment' if len(wizard.quotation_ids) == 1 else 'mass_mail'


    def _compute_quotation_without_email(self):
        import ipdb; ipdb.set_trace()
        for wizard in self:
            if len(wizard.quotation_ids) > 1:
                quotation = self.env['sale.order'].search([
                    ('id', 'in', self.env.context.get('active_ids')),
                    ('partner_id.email', '=', False)
                ])
                if quotation:
                    wizard.quotation_without_email = "%s\n%s" % (
                        _("The following quotation(s) will not be sent by email, because the customer(s) don't have email address."),
                        "\n".join([q.name for q in quotation])
                        )
                else:
                    wizard.quotation_without_email = False
            else:
                wizard.quotation_without_email = False

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

    def send_and_print_action(self):
        self.ensure_one()
        # Send the mails in the correct language by splitting the ids per lang.
        # This should ideally be fixed in mail_compose_message, so when a fix is made there this whole commit should be reverted.
        # basically self.body (which could be manually edited) extracts self.template_id,
        # which is then not translated for each customer.
        if self.composition_mode == 'mass_mail' and self.template_id:
            active_ids = self.env.context.get('active_ids', self.res_id)
            active_records = self.env[self.model].browse(active_ids)
            langs = active_records.mapped('partner_id.lang')
            default_lang = get_lang(self.env)
            for lang in (set(langs) or [default_lang]):
                active_ids_lang = active_records.filtered(lambda r: r.partner_id.lang == lang).ids
                self_lang = self.with_context(active_ids=active_ids_lang, lang=lang)
                self_lang.onchange_template_id()
                self_lang._send_email()
        else:
            self._send_email()
        return {'type': 'ir.actions.act_window_close'}
