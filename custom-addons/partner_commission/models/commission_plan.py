# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import _, api, fields, models, tools
from odoo.exceptions import ValidationError


class CommissionPlan(models.Model):
    _name = 'commission.plan'
    _description = 'Commission plan'

    name = fields.Char('Name', required=True)
    active = fields.Boolean(default=True)
    product_id = fields.Many2one(
        'product.product',
        'Purchase Default Product',
        domain=[('purchase_ok', '=', True)],
        default=lambda self: self.env.ref('partner_commission.product_commission'),
        required=True)
    commission_rule_ids = fields.One2many('commission.rule', 'plan_id', 'Rules', copy=True)
    company_id = fields.Many2one('res.company')

    def _match_rules(self, product, template, pricelist):
        self.ensure_one()

        rule = self.env['commission.rule'].search([
            ('plan_id', '=', self.id),
            ('category_id', '=', product.categ_id.id),
            '|',
            ('product_id', '=', product.id),
            ('product_id', '=', False),
            '|',
            ('template_id', '=', template),
            ('template_id', '=', False),
            '|',
            ('pricelist_id', '=', pricelist),
            ('pricelist_id', '=', False),
        ], limit=1, order='sequence')

        return rule


class CommissionRule(models.Model):
    _name = 'commission.rule'
    _description = 'Commission rules management.'

    plan_id = fields.Many2one('commission.plan', 'Commission Plan', required=True, ondelete='cascade')
    category_id = fields.Many2one('product.category', 'Product Category', required=True, ondelete='cascade')
    product_id = fields.Many2one(
        'product.product',
        'Product',
        ondelete='cascade',
        help="If set, the rule does not apply to the whole category but only on the given product.\n"
        "The product must belong to the selected category.\n"
        "Use several rules if you need to match multiple products within a category.")
    template_id = fields.Many2one('sale.order.template', 'Sale Order Template', ondelete="cascade")
    pricelist_id = fields.Many2one('product.pricelist', string='Pricelist', ondelete="cascade")
    rate = fields.Float('Rate', required=True, default=0)
    is_capped = fields.Boolean('Capped', required=True, default=False, help='Whether the commission is capped.')
    max_commission = fields.Float('Max Commission', help="Maximum amount, specified in the currency of the pricelist, if given.")
    sequence = fields.Integer(string='Sequence')

    _sql_constraints = [
        ('check_rate', 'CHECK(rate >= 0 AND rate <= 100)', 'Rate should be between 0 and 100.'),
    ]

    @api.constrains('product_id', 'category_id')
    def _check_product_category(self):
        for rule in self:
            if rule.product_id and rule.product_id.categ_id != rule.category_id:
                raise ValidationError(_('Product %s does not belong to category %s', rule.product_id.code, rule.category_id.name))

    @api.onchange('is_capped')
    def _onchange_is_capped(self):
        if not self.is_capped:
            self.max_commission = 0

    def _auto_init(self):
        result = super(CommissionRule, self)._auto_init()
        # Unique index to handle product_id, template_id, pricelist_id even if those are null (not possible using a constraint).
        tools.create_unique_index(
            self._cr,
            'commission_rule_check_combination_unique_index',
            self._table,
            ['plan_id', 'category_id', 'COALESCE(product_id, -1)', 'COALESCE(template_id, -1)', 'COALESCE(pricelist_id, -1)']
        )
        return result
