# -*- coding: utf-8 -*-
from openerp import models, fields, api


class account_analytic_account_wizard(models.TransientModel):
    _name = 'account.analytic.account.wizard'

    def _default_account(self):
        return self.env['account.analytic.account'].browse(self._context.get('active_id'))

    account_id = fields.Many2one('account.analytic.account', string="Contract", required=True, default=_default_account)
    lines = fields.One2many('account.analytic.transient.option', 'wizard_id', string="Options")

    @api.multi
    def create_sale_order(self):
        template_id = self.env['account.analytic.account'].browse(self.env.context.get('active_id')).template_id
        sale_order_obj = self.env['sale.order']
        order = sale_order_obj.create({
            'partner_id': self.account_id.partner_id.id,
            'project_id': self.account_id.id,
            'team_id': self.env['ir.model.data'].get_object_reference('website', 'salesteam_website_sales')[1],
            })
        for line in self.lines:
            for option in template_id.option_invoice_line_ids:
                if line.product_id == option.product_id:
                    line.name = option.name
            self.account_id.partial_invoice_line(order, line)
        email_act = order.action_quotation_send()
        # send the email
        if email_act and email_act.get('context'):
            composer_obj = self.env['mail.compose.message']
            composer_values = {}
            email_ctx = email_act['context']
            template_values = [
                email_ctx.get('default_template_id'),
                email_ctx.get('default_composition_mode'),
                email_ctx.get('default_model'),
                email_ctx.get('default_res_id'),
            ]
            composer_values.update(composer_obj.sudo().onchange_template_id(*template_values).get('value', {}))
            for key in ['attachment_ids', 'partner_ids']:
                if composer_values.get(key):
                    composer_values[key] = [(6, 0, composer_values[key])]
            composer_id = composer_obj.with_context(email_ctx).create(composer_values)
            composer_id.with_context(email_ctx).send_mail()
        body = """
        <div>Sale Order for new option(s) created.</div>
        <div>&nbsp;&nbsp;&bull; <b>Sale Order</b>: """+order.name+"""</div>"""
        options = ["<div>&nbsp;&nbsp;&bull; <b>Option</b>: " + line.product_id.name_template + "</div>" for line in order.order_line]
        body += ' '.join(options)
        self.account_id.message_post(body=body)
        return {
            "type": "ir.actions.act_window",
            "res_model": "sale.order",
            "views": [[False, "form"]],
            "res_id": order.id,
        }


class account_analytic_transient_option(models.TransientModel):
    _name = "account.analytic.transient.option"
    _inherit = "account.analytic.invoice.line.option"

    def _product_domain(self):
        template_id = self.env['account.analytic.account'].browse(self.env.context.get('active_id')).template_id
        return [('id', 'in', [option.product_id.id for option in template_id.option_invoice_line_ids] + [line.product_id.id for line in template_id.recurring_invoice_line_ids])]

    wizard_id = fields.Many2one('account.analytic.account.wizard')
    product_id = fields.Many2one('product.product', domain=_product_domain)