# -*- encoding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError

import re


class Efaktur(models.Model):
    _name = "l10n_id_efaktur.efaktur.range"
    _description = "Available E-faktur range"

    company_id = fields.Many2one('res.company', required=True, default=lambda self: self.env.company)
    max = fields.Char(compute='_compute_default', store=True, readonly=False)
    min = fields.Char(compute='_compute_default', store=True, readonly=False)
    available = fields.Integer(readonly=True)
    next_num = fields.Integer(compute="_compute_next_num", store=True)

    @api.depends('max', 'available')
    def _compute_next_num(self):
        for record in self:
            record.next_num = int(record.max) - record.available + 1

    @api.model
    def pop_number(self, company_id):
        erange = self.search([('company_id', '=', company_id)], order="next_num ASC", limit=1)

        if not erange:
            return None

        popped = erange.next_num
        erange.available -= 1

        return popped

    @api.model
    def push_number(self, company_id, number):
        # if released number is the last released number from a range, extend the availability
        erange = self.search([('company_id', '=', company_id), ('next_num', '=', int(number) + 1)])
        if erange:
            erange.available += 1
            return

        # if the released number is not the last used number from any range, find the range it belongs and split it
        # i.e range: 1 - 10, available=5, next_number=6, release 3
        # split 1-10 to 1-3 available=1 AND 4-10 available=5
        erange = self.search([('company_id', '=', company_id), ('min', '<=', number), ('max', '>=', number)])
        if erange:
            if erange.min == erange.max:
                erange.available += 1
            else:
                maximum = erange.max
                available = erange.available
                erange.write({
                    'available': 1,
                    'max': number
                })

                self.create({
                    'company_id': company_id,
                    'min': '%013d' % (int(number) + 1),
                    'max': maximum,
                    'available': available  # keep original available to not change next_num of that range
                })

    @api.constrains('min', 'max')
    def _constrains_min_max(self):
        for record in self:
            if not len(record.min) == 13 or not len(record.max) == 13:
                raise ValidationError(_("There should be 13 digits in each number."))

            if record.min[:-8] != record.max[:-8]:
                raise ValidationError(_("First 5 digits should be same in Start Number and End Number."))

            if int(record.min[-8:]) > int(record.max[-8:]):
                raise ValidationError(_("Last 8 digits of End Number should be greater than the last 8 digit of Start Number"))

            if (int(record.max) - int(record.min)) > 10000:
                raise ValidationError(_("The difference between the two numbers must not be greater than 10.000"))

            # The number of records should always be very small, so it is ok to search in loop
            if self.search_count([
                '&', ('id', '!=', record.id), '|', '|',
                '&', ('min', '<=', record.max), ('max', '>=', record.max),
                '&', ('min', '<=', record.min), ('max', '>=', record.min),
                '&', ('min', '>=', record.min), ('max', '<=', record.max),
            ], limit=1):
                raise ValidationError(_('Efaktur interleaving range detected'))

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if not vals.get('available'):
                vals['available'] = 1 + int(vals['max']) - int(vals['min'])
        return super().create(vals_list)

    def write(self, vals):
        if 'max' in vals and 'available' not in vals:
            # if it's lower than used numbers, error
            if int(vals['max']) < self.next_num and 'available' not in vals:
                raise ValidationError(_("You are not allowed to change the max to a number lower than already used"))
            diff = int(vals['max']) - int(self.max)
            vals['available'] = self.available + diff
        if 'min' in vals and 'available' not in vals:
            # if range has been been used, raise error when changing min
            if self.next_num > int(self.min):
                raise ValidationError(_("You are not allowed to change the min of a range that is already in use"))
            # if range was unused, adapt it according to how min is changed
            if int(self.min) == self.next_num:
                diff = int(self.min) - int(vals['min'])
                vals['available'] = self.available + diff
        return super().write(vals)

    @api.depends('company_id')
    def _compute_default(self):
        for record in self:
            query = """
                SELECT MAX(SUBSTRING(l10n_id_tax_number FROM 4))
                FROM account_move
                WHERE l10n_id_tax_number IS NOT NULL
                  AND company_id = %s
            """
            self.env.cr.execute(query, [record.company_id.id])
            max_used = int(self.env.cr.fetchone()[0] or 0)
            max_available = int(self.env['l10n_id_efaktur.efaktur.range'].search([('company_id', '=', record.company_id.id)], order='max DESC', limit=1).max)
            record.min = record.max = '%013d' % (max(max_available, max_used) + 1)

    @api.onchange('min')
    def _onchange_min(self):
        min_val = re.sub(r'\D', '', str(self.min)) or 0
        self.min = '%013d' % int(min_val)
        if not self.max or int(self.min) > int(self.max):
            self.max = self.min

    @api.onchange('max')
    def _onchange_max(self):
        max_val = re.sub(r'\D', '', str(self.max)) or 0
        self.max = '%013d' % int(max_val)
        if not self.min or int(self.min) > int(self.max):
            self.min = self.max
