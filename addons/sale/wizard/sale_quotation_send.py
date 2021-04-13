
# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _
from odoo.exceptions import UserError
from odoo.tools.misc import get_lang

class SaleQuotationSend(models.TransientModel):
    _name = 'sale.quotation.send'
    _description = 'Sale Quotation Send'

    active_draft_ids = fields.Many2many(
        string="Selected quotations draft",
        comodel_name='sale.order',
        relation='sale_order_draft_sale_quotation_send_rel',
        help="List of the selected quotation's ids in the state \"draft\".",
    )
    active_sale_ids = fields.Many2many(
        string="Sale Orders",
        comodel_name='sale.order',
        relation='sale_order_sale_sale_quotation_send_rel',
        help="List of the selected quotation's ids in the state \"sent\" or \"sale\".",
    )
    draft_template_id = fields.Many2one(
        string="Use template for Quotations",
        comodel_name='mail.template',
        index=True,
        domain='[("model", "=", "sale.order")]'
    )
    sale_template_id = fields.Many2one(
        string="Use template for Sale Orders",
        comodel_name='mail.template',
        index=True,
        domain='[("model", "=", "sale.order")]'
    )

    @api.model
    def default_get(self, fields):
        default = super(SaleQuotationSend, self).default_get(fields)
        active_draft_ids = self._context.get('active_draft_ids')
        active_sale_ids = self._context.get('active_sale_ids')

        draft_template_id = self._context.get('default_draft_template_id')
        sale_template_id = self._context.get('default_sale_template_id')

        if not active_draft_ids and not self.active_sale_ids:
            raise UserError(_("You should select at least one quotation."))

        default.update({
            'active_draft_ids': active_draft_ids,
            'active_sale_ids': active_sale_ids,
            'draft_template_id': draft_template_id,
            'sale_template_id': sale_template_id,
        })

        return default

    def _compute_quotation_has_email(self):
        # TODO REFACTOR (delete quotation_has_email, to only get a variable)
        for wizard in self:
            if len(wizard.quotation_ids) >= 1:
                quotation = self.env['sale.order'].search([
                    ('id', 'in', self.env.context.get('active_ids')),
                    ('partner_id.email', '=', False)
                ])
                if quotation:
                    wizard.quotation_has_email = "%s\n%s" % (
                        _("The following quotation(s) will not be sent by email, because the customer(s) don't have email address."),
                        "\n".join([q.name for q in quotation])
                        )
                    raise UserError(_(wizard.quotation_has_email))
                else:
                    wizard.quotation_has_email = False
            else:
                wizard.quotation_has_email = False

    def _send_email(self):
        # with_context : we don't want to reimport the file we just exported.
        self.composer_id.with_context(mail_notify_author=self.env.user.partner_id in self.composer_id.partner_ids).send_mail()
        if self.env.context.get('mark_so_as_sent'):
            #TODO ADD .with_context(tracking_disable=True) ?
            self.quotation_ids.filtered(lambda o: o.state == 'draft').write({'state': 'sent'})

    def send_quotation_action(self):
        self.ensure_one()
        # Send the mails in the correct language by splitting the ids per lang.
        # This should ideally be fixed in mail_compose_message, so when a fix is made there this whole commit should be reverted.
        # basically self.body (which could be manually edited) extracts self.template_id,
        # which is then not translated for each customer.

        #default_lang = get_lang(self.env)
        if self.active_draft_ids:
            for quotation in self.active_draft_ids:
                self.draft_template_id.send_mail(quotation.id, force_send=True)

            # langs_draft = self.active_draft_ids.mapped('partner_id.lang')
            # for lang in (set(langs_draft) or [default_lang]):
            #     active_ids_lang = self.active_draft_ids.filtered(lambda r: r.partner_id.lang == lang).ids
            #     self_lang = self.with_context(active_ids=active_ids_lang, lang=lang)
            #     self_lang.with_context(force_send=True).message_post_with_template(self.draft_template_id)

        if self.active_sale_ids:
            for sale_order in self.active_sale_ids:
                self.sale_template_id.send_mail(sale_order.id, force_send=True)

            # langs_sale = self.active_sale_ids.mapped('partner_id.lang')
            # for lang in (set(langs_sale) or [default_lang]):
            #     active_ids_lang = self.active_sale_ids.filtered(lambda r: r.partner_id.lang == lang).ids
            #     self_lang = self.with_context(active_ids=active_ids_lang, lang=lang)
            #     self_lang.with_context(force_send=True).message_post_with_template(self.sale_template_id)

        return {'type': 'ir.actions.act_window_close'}
