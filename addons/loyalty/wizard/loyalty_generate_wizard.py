# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import _, api, fields, models
from odoo.exceptions import ValidationError
from odoo.osv import expression

class LoyaltyGenerateWizard(models.TransientModel):
    _name = 'loyalty.generate.wizard'
    _description = 'Generate Coupons'

    program_id = fields.Many2one('loyalty.program', required=True, default=lambda self: self.env.context.get('active_id', False) or self.env.context.get('default_program_id', False))
    program_type = fields.Selection(related='program_id.program_type')

    mode = fields.Selection([
        ('anonymous', 'Anonymous Customers'),
        ('selected', 'Selected Customers')],
        string='For', required=True, default='anonymous'
    )

    customer_ids = fields.Many2many('res.partner', string='Customers')
    customer_tag_ids = fields.Many2many('res.partner.category', string='Customer Tags')

    coupon_qty = fields.Integer('Quantity',
        compute='_compute_coupon_qty', readonly=False, store=True)
    points_granted = fields.Float('Grant', required=True, default=1)
    points_name = fields.Char(related='program_id.portal_point_name', readonly=True)
    valid_until = fields.Date()
    will_send_mail = fields.Boolean(compute='_compute_will_send_mail')
    confirmation_message = fields.Char(compute='_compute_confirmation_message')
    description = fields.Text(string="Description")

    def _get_partners(self):
        self.ensure_one()
        if self.mode != 'selected':
            return self.env['res.partner']
        domains = []
        if self.customer_ids:
            domains.append([('id', 'in', self.customer_ids.ids)])
        if self.customer_tag_ids:
            domains.append([('category_id', 'in', self.customer_tag_ids.ids)])
        return self.env['res.partner'].search(expression.OR(domains) if domains else [])

    @api.depends('program_type', 'points_granted', 'coupon_qty')
    def _compute_confirmation_message(self):
        self.confirmation_message = False
        for wizard in self:
            program_desc = dict(wizard._fields['program_type']._description_selection(wizard.env))
            wizard.confirmation_message = _("You're about to generate %(program_type)s with a value of %(value)s for %(customer_number)i customers",
                program_type=program_desc[wizard.program_type],
                value=wizard.points_granted,
                customer_number=wizard.coupon_qty,
            )

    @api.depends('customer_ids', 'customer_tag_ids', 'mode')
    def _compute_coupon_qty(self):
        for wizard in self:
            if wizard.mode == 'selected':
                wizard.coupon_qty = len(wizard._get_partners())
            else:
                wizard.coupon_qty = wizard.coupon_qty or 0

    @api.depends("mode", "program_id")
    def _compute_will_send_mail(self):
        for wizard in self:
            wizard.will_send_mail = wizard.mode == 'selected' and 'create' in wizard.program_id.mapped('communication_plan_ids.trigger')

    def _get_coupon_values(self, partner):
        self.ensure_one()
        return {
            'program_id': self.program_id.id,
            'points': self.points_granted,
            'expiration_date': self.valid_until,
            'partner_id': partner.id if self.mode == 'selected' else False,
        }

    def generate_coupons(self):
        if any(not wizard.program_id for wizard in self):
            raise ValidationError(_("Can not generate coupon, no program is set."))
        if any(wizard.coupon_qty <= 0 for wizard in self):
            raise ValidationError(_("Invalid quantity."))
        coupon_create_vals = []
        for wizard in self:
            customers = wizard._get_partners() or range(wizard.coupon_qty)
            for partner in customers:
                coupon_create_vals.append(wizard._get_coupon_values(partner))
        coupons = self.env['loyalty.card'].create(coupon_create_vals)
        self.env['loyalty.history'].create([
            {
                'description': self.description or _("Gift For Customer"),
                'card_id': coupon.id,
                'issued': self.points_granted,
            } for coupon in coupons
        ])
        return True
