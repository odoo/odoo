# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import timedelta

from odoo import SUPERUSER_ID, api, fields, models, _
from odoo.exceptions import ValidationError
from odoo.tools import is_html_empty


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    sale_order_template_id = fields.Many2one(
        comodel_name='sale.order.template',
        string="Quotation Template",
        compute='_compute_sale_order_template_id',
        store=True, readonly=False, check_company=True, precompute=True,
        domain="['|', ('company_id', '=', False), ('company_id', '=', company_id)]")
    sale_order_option_ids = fields.One2many(
        comodel_name='sale.order.option', inverse_name='order_id',
        string="Optional Products Lines",
        copy=True)

    #=== COMPUTE METHODS ===#

    # Do not make it depend on `company_id` field
    # It is triggered manually by the _onchange_company_id below iff the SO has not been saved.
    def _compute_sale_order_template_id(self):
        for order in self:
            company_template = order.company_id.sale_order_template_id
            if company_template and order.sale_order_template_id != company_template:
                if 'website_id' in self._fields and order.website_id:
                    # don't apply quotation template for order created via eCommerce
                    continue
                order.sale_order_template_id = order.company_id.sale_order_template_id.id

    @api.depends('partner_id', 'sale_order_template_id')
    def _compute_note(self):
        super()._compute_note()
        for order in self.filtered('sale_order_template_id'):
            template = order.sale_order_template_id.with_context(lang=order.partner_id.lang)
            order.note = template.note if not is_html_empty(template.note) else order.note

    @api.depends('sale_order_template_id')
    def _compute_require_signature(self):
        super()._compute_require_signature()
        for order in self.filtered('sale_order_template_id'):
            order.require_signature = order.sale_order_template_id.require_signature

    @api.depends('sale_order_template_id')
    def _compute_require_payment(self):
        super()._compute_require_payment()
        for order in self.filtered('sale_order_template_id'):
            order.require_payment = order.sale_order_template_id.require_payment

    @api.depends('sale_order_template_id')
    def _compute_prepayment_percent(self):
        super()._compute_prepayment_percent()
        for order in self.filtered('sale_order_template_id'):
            if order.require_payment:
                order.prepayment_percent = order.sale_order_template_id.prepayment_percent

    @api.depends('sale_order_template_id')
    def _compute_validity_date(self):
        super()._compute_validity_date()
        for order in self.filtered('sale_order_template_id'):
            validity_days = order.sale_order_template_id.number_of_days
            if validity_days > 0:
                order.validity_date = fields.Date.context_today(order) + timedelta(validity_days)

    @api.depends('sale_order_template_id')
    def _compute_journal_id(self):
        super()._compute_journal_id()
        for order in self.filtered('sale_order_template_id'):
            order.journal_id = order.sale_order_template_id.journal_id

    #=== CONSTRAINT METHODS ===#

    @api.constrains('company_id', 'sale_order_option_ids')
    def _check_optional_product_company_id(self):
        for order in self:
            companies = order.sale_order_option_ids.product_id.company_id
            if companies and companies != order.company_id:
                bad_products = order.sale_order_option_ids.product_id.filtered(lambda p: p.company_id and p.company_id != order.company_id)
                raise ValidationError(_(
                    "Your quotation contains products from company %(product_company)s whereas your quotation belongs to company %(quote_company)s. \n Please change the company of your quotation or remove the products from other companies (%(bad_products)s).",
                    product_company=', '.join(companies.mapped('display_name')),
                    quote_company=order.company_id.display_name,
                    bad_products=', '.join(bad_products.mapped('display_name')),
                ))

    #=== ONCHANGE METHODS ===#

    @api.onchange('company_id')
    def _onchange_company_id(self):
        """Trigger quotation template recomputation on unsaved records company change"""
        if self._origin.id:
            return
        self._compute_sale_order_template_id()

    @api.onchange('sale_order_template_id')
    def _onchange_sale_order_template_id(self):
        if not self.sale_order_template_id:
            return

        sale_order_template = self.sale_order_template_id.with_context(lang=self.partner_id.lang)

        order_lines_data = [fields.Command.clear()]
        order_lines_data += [
            fields.Command.create(line._prepare_order_line_values())
            for line in sale_order_template.sale_order_template_line_ids
        ]

        # set first line to sequence -99, so a resequence on first page doesn't cause following page
        # lines (that all have sequence 10 by default) to get mixed in the first page
        if len(order_lines_data) >= 2:
            order_lines_data[1][2]['sequence'] = -99

        self.order_line = order_lines_data

        option_lines_data = [fields.Command.clear()]
        option_lines_data += [
            fields.Command.create(option._prepare_option_line_values())
            for option in sale_order_template.sale_order_template_option_ids
        ]

        self.sale_order_option_ids = option_lines_data

    #=== ACTION METHODS ===#

    def _get_confirmation_template(self):
        self.ensure_one()
        return self.sale_order_template_id.mail_template_id or super()._get_confirmation_template()

    def action_confirm(self):
        res = super().action_confirm()

        if self.env.context.get('send_email'):
            # Mail already sent in super method
            return res

        # When an order is confirmed from backend (send_email=False), if the quotation template has
        # a specified mail template, send it as it's probably meant to share additional information.
        for order in self:
            if order.sale_order_template_id.mail_template_id:
                order._send_order_notification_mail(order.sale_order_template_id.mail_template_id)
        return res

    def _recompute_prices(self):
        super()._recompute_prices()
        # Special case: we want to overwrite the existing discount on _recompute_prices call
        # i.e. to make sure the discount is correctly reset
        # if pricelist discount_policy is different than when the price was first computed.
        self.sale_order_option_ids.discount = 0.0
        self.sale_order_option_ids._compute_price_unit()
        self.sale_order_option_ids._compute_discount()

    def _can_be_edited_on_portal(self):
        self.ensure_one()
        return self.state in ('draft', 'sent')
