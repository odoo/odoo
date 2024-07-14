# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import date

from odoo import _, api, fields, models
from odoo.exceptions import ValidationError
from odoo.osv import expression


class L10nHkRental(models.Model):
    _name = 'l10n_hk.rental'
    _description = "Hong Kong: Rental"

    name = fields.Char("Rental Reference", required=True)
    active = fields.Boolean(default=True)
    address = fields.Char("Address")
    state = fields.Selection([
        ('draft', 'Draft'),
        ('open', 'Running'),
        ('close', 'Expired'),
        ('cancel', 'Cancelled'),
    ], default='draft', required=True, copy=False)
    employee_id = fields.Many2one(
        'hr.employee',
        string='Employee',
        domain="['|', ('company_id', '=', False), ('company_id', '=', company_id)]",
        required=True)
    date_start = fields.Date(
        'Start Date', required=True, default=fields.Date.today, index=True)
    date_end = fields.Date('End Date')
    amount = fields.Monetary(
        "Rental Amount", required=True)
    nature = fields.Selection(
        selection=[
            ('flat', 'Flat'),
            ('hotel', 'Hotel')
        ], string='Rental Type', default='flat', required=True)
    company_id = fields.Many2one(
        'res.company',
        store=True,
        readonly=False,
        compute='_compute_company_id',
        default=lambda self: self.env.company,
        required=True)
    currency_id = fields.Many2one(
        string="Currency",
        related='company_id.currency_id',
        readonly=True)
    rentals_count = fields.Integer(related='employee_id.l10n_hk_rentals_count')

    @api.depends('employee_id')
    def _compute_company_id(self):
        for rental in self:
            if not rental.employee_id:
                continue
            rental.company_id = rental.employee_id.company_id

    @api.constrains('employee_id', 'state', 'date_start', 'date_end')
    def _check_current_rental(self):
        for rental in self:
            if rental.state in ['draft', 'cancel'] or not rental.employee_id:
                continue
            domain = [
                ('id', '!=', rental.id),
                ('employee_id', '=', rental.employee_id.id),
                ('company_id', '=', rental.company_id.id),
                ('state', 'in', ['open', 'close']),
            ]
            if not rental.date_end:
                start_domain = []
                end_domain = ['|', ('date_end', '>=', rental.date_start), ('date_end', '=', False)]
            else:
                start_domain = [('date_start', '<=', rental.date_end)]
                end_domain = ['|', ('date_end', '>', rental.date_start), ('date_end', '=', False)]

            domain = expression.AND([domain, start_domain, end_domain])
            if self.search_count(domain):
                raise ValidationError(_(
                    'Rental %(rental)s: employee %(employee)s already has a rental running during this period.',
                    rental=rental.name, employee=rental.employee_id.name,
                ))

    @api.constrains('date_start', 'date_end')
    def _check_dates(self):
        for rental in self:
            if rental.date_end and rental.date_start > rental.date_end:
                raise ValidationError(_(
                    'Rental %(rental)s: start date (%(start)s) must be earlier than rental end date (%(end)s).',
                    rental=rental.name, start=rental.date_start, end=rental.date_end,
                ))

    @api.model
    def update_state(self):
        rentals_to_close = self.search([
            ('state', '=', 'open'),
            ('date_end', '<=', fields.Date.to_string(date.today())),
        ])
        if rentals_to_close:
            rentals_to_close.write({'state': 'close'})

        rentals_to_open = self.search([
            ('state', '=', 'draft'),
            ('date_start', '<=', fields.Date.to_string(date.today())),
        ])
        if rentals_to_open:
            rentals_to_open.write({'state': 'open'})
        return True

    def _assign_open_rental(self):
        for rental in self:
            rental.employee_id.sudo().write({'l10n_hk_rental_id': rental.id})

    @api.model_create_multi
    def create(self, vals_list):
        rentals = super().create(vals_list)
        rentals.filtered(lambda r: r.state == 'open')._assign_open_rental()
        return rentals

    def write(self, vals):
        old_state = {c.id: c.state for c in self}
        res = super().write(vals)
        new_state = {c.id: c.state for c in self}
        if vals.get('state') == 'open':
            self._assign_open_rental()
        for rental in self:
            if rental == rental.sudo().employee_id.l10n_hk_rental_id \
                and old_state[rental.id] == 'open' \
                    and new_state[rental.id] != 'open':
                running_rental = self.env['l10n_hk.rental'].search([
                    ('employee_id', '=', rental.employee_id.id),
                    ('company_id', '=', rental.company_id.id),
                    ('state', '=', 'open'),
                ])
                if running_rental:
                    rental.employee_id.l10n_hk_rental_id = running_rental[0]
                else:
                    rental.employee_id.l10n_hk_rental_id = False
        return res

    def action_open_rentals_list(self):
        self.ensure_one()
        action = self.env["ir.actions.actions"]._for_xml_id("l10n_hk_hr_payroll.action_l10n_hk_rental")
        action.update({
            'domain': [('employee_id', '=', self.employee_id.id)],
            'views': [[False, 'list'], [False, 'form']],
            'context': {'default_employee_id': self.employee_id.id},
        })
        return action
