# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError


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

    sale_order_template_line_ids = fields.One2many(
        comodel_name='sale.order.template.line', inverse_name='sale_order_template_id',
        string="Lines",
        copy=True)
    sale_order_template_option_ids = fields.One2many(
        comodel_name='sale.order.template.option', inverse_name='sale_order_template_id',
        string="Optional Products",
        copy=True)

    #=== COMPUTE METHODS ===#

    @api.depends('company_id')
    def _compute_require_signature(self):
        for order in self:
            order.require_signature = (order.company_id or order.env.company).portal_confirmation_sign

    @api.depends('company_id')
    def _compute_require_payment(self):
        for order in self:
            order.require_payment = (order.company_id or order.env.company).portal_confirmation_pay

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
                    self.create_or_update_translations(
                        model_name='sale.order.template.line,name', lang_code=lang.code,
                        res_id=line.id, src=line.name,
                        value=line.product_id.with_context(lang=lang.code).get_product_multiline_description_sale())
            for option in self.sale_order_template_option_ids:
                if option.name == option.product_id.get_product_multiline_description_sale():
                    self.create_or_update_translations(
                        model_name='sale.order.template.option,name', lang_code=lang.code,
                        res_id=option.id, src=option.name,
                        value=option.product_id.with_context(lang=lang.code).get_product_multiline_description_sale())

    def create_or_update_translations(self, model_name, lang_code, res_id, src, value):
        data = {
            'type': 'model',
            'name': model_name,
            'lang': lang_code,
            'res_id': res_id,
            'src': src,
            'value': value,
            'state': 'inprogress',
        }
        existing_trans = self.env['ir.translation'].search([
            ('name', '=', model_name),
            ('res_id', '=', res_id),
            ('lang', '=', lang_code)
        ])
        if not existing_trans:
            self.env['ir.translation'].create(data)
        else:
            existing_trans.write(data)


class SaleOrderTemplateLine(models.Model):
    _name = "sale.order.template.line"
    _description = "Quotation Template Line"
    _order = 'sale_order_template_id, sequence, id'

    _sql_constraints = [
        ('accountable_product_id_required',
            "CHECK(display_type IS NOT NULL OR (product_id IS NOT NULL AND product_uom_id IS NOT NULL))",
            "Missing required product and UoM on accountable sale quote line."),

        ('non_accountable_fields_null',
            "CHECK(display_type IS NULL OR (product_id IS NULL AND product_uom_qty = 0 AND product_uom_id IS NULL))",
            "Forbidden product, unit price, quantity, and UoM on non-accountable sale quote line"),
    ]

    sale_order_template_id = fields.Many2one(
        comodel_name='sale.order.template',
        string='Quotation Template Reference',
        index=True, required=True,
        ondelete='cascade')
    sequence = fields.Integer(
        string="Sequence",
        help="Gives the sequence order when displaying a list of sale quote lines.",
        default=10)

    company_id = fields.Many2one(
        related='sale_order_template_id.company_id', store=True, index=True)

    product_id = fields.Many2one(
        comodel_name='product.product',
        check_company=True,
        domain="[('sale_ok', '=', True), ('company_id', 'in', [company_id, False])]")

    name = fields.Text(
        string="Description",
        compute='_compute_name',
        store=True, readonly=False, precompute=True,
        required=True,
        translate=True)

    product_uom_id = fields.Many2one(
        comodel_name='uom.uom',
        string="Unit of Measure",
        compute='_compute_product_uom_id',
        store=True, readonly=False, precompute=True,
        domain="[('category_id', '=', product_uom_category_id)]")
    product_uom_category_id = fields.Many2one(related='product_id.uom_id.category_id')
    product_uom_qty = fields.Float(
        string='Quantity',
        required=True,
        digits='Product Unit of Measure',
        default=1)

    display_type = fields.Selection([
        ('line_section', "Section"),
        ('line_note', "Note")], default=False, help="Technical field for UX purpose.")

    #=== COMPUTE METHODS ===#

    @api.depends('product_id')
    def _compute_name(self):
        for option in self:
            if not option.product_id:
                continue
            option.name = option.product_id.get_product_multiline_description_sale()

    @api.depends('product_id')
    def _compute_product_uom_id(self):
        for option in self:
            option.product_uom_id = option.product_id.uom_id

    #=== CRUD METHODS ===#

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('display_type', self.default_get(['display_type'])['display_type']):
                vals.update(product_id=False, product_uom_qty=0, product_uom_id=False)
        return super().create(vals_list)

    def write(self, values):
        if 'display_type' in values and self.filtered(lambda line: line.display_type != values.get('display_type')):
            raise UserError(_("You cannot change the type of a sale quote line. Instead you should delete the current line and create a new line of the proper type."))
        return super().write(values)


class SaleOrderTemplateOption(models.Model):
    _name = "sale.order.template.option"
    _description = "Quotation Template Option"
    _check_company_auto = True

    sale_order_template_id = fields.Many2one(
        comodel_name='sale.order.template',
        string="Quotation Template Reference",
        index=True, required=True,
        ondelete='cascade')

    company_id = fields.Many2one(
        related='sale_order_template_id.company_id', store=True, index=True)

    product_id = fields.Many2one(
        comodel_name='product.product',
        required=True, check_company=True,
        domain="[('sale_ok', '=', True), ('company_id', 'in', [company_id, False])]")

    name = fields.Text(
        string="Description",
        compute='_compute_name',
        store=True, readonly=False, precompute=True,
        required=True, translate=True)

    uom_id = fields.Many2one(
        comodel_name='uom.uom',
        string="Unit of Measure",
        compute='_compute_uom_id',
        store=True, readonly=False,
        required=True, precompute=True,
        domain="[('category_id', '=', product_uom_category_id)]")
    product_uom_category_id = fields.Many2one(related='product_id.uom_id.category_id')
    quantity = fields.Float(
        string="Quantity",
        required=True,
        digits='Product Unit of Measure',
        default=1)

    #=== COMPUTE METHODS ===#

    @api.depends('product_id')
    def _compute_name(self):
        for option in self:
            if not option.product_id:
                continue
            option.name = option.product_id.get_product_multiline_description_sale()

    @api.depends('product_id')
    def _compute_uom_id(self):
        for option in self:
            option.uom_id = option.product_id.uom_id
