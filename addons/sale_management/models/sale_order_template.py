# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class SaleOrderTemplate(models.Model):
    _name = "sale.order.template"
    _description = "Quotation Template"

    active = fields.Boolean(
        default=True,
        help="If unchecked, it will allow you to hide the quotation template without removing it.")
    company_id = fields.Many2one(comodel_name='res.company')

    name = fields.Char(string="Quotation Template", required=True)
    note = fields.Html(string="Terms and conditions", translate=True)

    mail_template_id = fields.Many2one(
        comodel_name='mail.template',
        string="Confirmation Mail",
        domain=[('model', '=', 'sale.order')],
        help="This e-mail template will be sent on confirmation. Leave empty to send nothing.")
    number_of_days = fields.Integer(
        string="Quotation Duration",
        help="Number of days for the validity date computation of the quotation")

    require_signature = fields.Boolean(
        string="Online Signature",
        compute='_compute_require_signature',
        store=True, readonly=False,
        help="Request a online signature to the customer in order to confirm orders automatically.")
    require_payment = fields.Boolean(
        string="Online Payment",
        compute='_compute_require_payment',
        store=True, readonly=False,
        help="Request an online payment to the customer in order to confirm orders automatically.")
    prepayment_percent = fields.Float(
        string="Prepayment percentage",
        compute="_compute_prepayment_percent",
        store=True, readonly=False,
        help="The percentage of the amount needed to be paid to confirm quotations.")

    sale_order_template_line_ids = fields.One2many(
        comodel_name='sale.order.template.line', inverse_name='sale_order_template_id',
        string="Lines",
        copy=True)
    sale_order_template_option_ids = fields.One2many(
        comodel_name='sale.order.template.option', inverse_name='sale_order_template_id',
        string="Optional Products",
        copy=True)
    journal_id = fields.Many2one(
        'account.journal', string="Invoicing Journal",
        domain=[('type', '=', 'sale')], company_dependent=True, check_company=True,
        help="If set, SO with this template will invoice in this journal; "
             "otherwise the sales journal with the lowest sequence is used.")

    #=== COMPUTE METHODS ===#

    @api.depends('company_id')
    def _compute_require_signature(self):
        for order in self:
            order.require_signature = (order.company_id or order.env.company).portal_confirmation_sign

    @api.depends('company_id')
    def _compute_require_payment(self):
        for order in self:
            order.require_payment = (order.company_id or order.env.company).portal_confirmation_pay

    @api.depends('company_id', 'require_payment')
    def _compute_prepayment_percent(self):
        for template in self:
            template.prepayment_percent = (
                template.company_id or template.env.company
            ).prepayment_percent

    #=== ONCHANGE METHODS ===#

    @api.onchange('prepayment_percent')
    def _onchange_prepayment_percent(self):
        for template in self:
            if not template.prepayment_percent:
                template.require_payment = False

    #=== CONSTRAINT METHODS ===#

    @api.constrains('company_id', 'sale_order_template_line_ids', 'sale_order_template_option_ids')
    def _check_company_id(self):
        for template in self:
            companies = template.mapped('sale_order_template_line_ids.product_id.company_id') | template.mapped('sale_order_template_option_ids.product_id.company_id')
            if len(companies) > 1:
                raise ValidationError(_("Your template cannot contain products from multiple companies."))
            elif companies and companies != template.company_id:
                raise ValidationError(_(
                    "Your template contains products from company %(product_company)s whereas your template belongs to company %(template_company)s. \n Please change the company of your template or remove the products from other companies.",
                    product_company=', '.join(companies.mapped('display_name')),
                    template_company=template.company_id.display_name,
                ))

    @api.constrains('prepayment_percent')
    def _check_prepayment_percent(self):
        for template in self:
            if template.require_payment and not (0 < template.prepayment_percent <= 1.0):
                raise ValidationError(_("Prepayment percentage must be a valid percentage."))

    #=== CRUD METHODS ===#

    @api.model_create_multi
    def create(self, vals_list):
        records = super().create(vals_list)
        records._update_product_translations()
        return records

    def write(self, vals):
        if 'active' in vals and not vals.get('active'):
            companies = self.env['res.company'].sudo().search([('sale_order_template_id', 'in', self.ids)])
            companies.sale_order_template_id = None
        result = super().write(vals)
        self._update_product_translations()
        return result

    def _update_product_translations(self):
        languages = self.env['res.lang'].search([('active', '=', 'true')])
        for lang in languages:
            for line in self.sale_order_template_line_ids:
                if line.name == line.product_id.get_product_multiline_description_sale():
                    line.with_context(lang=lang.code).name = line.product_id.with_context(lang=lang.code).get_product_multiline_description_sale()
            for option in self.sale_order_template_option_ids:
                if option.name == option.product_id.get_product_multiline_description_sale():
                    option.with_context(lang=lang.code).name = option.product_id.with_context(lang=lang.code).get_product_multiline_description_sale()
