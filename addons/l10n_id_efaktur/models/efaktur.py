# -*- encoding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError

import re


class Efaktur(models.Model):
    _name = "l10n_id_efaktur.efaktur.range"
    _description = "Available E-faktur range"
    _rec_names_search = ["min", "max"]

    company_id = fields.Many2one('res.company', required=True, default=lambda self: self.env.company)
    max = fields.Char(required=True)
    min = fields.Char(required=True)
    available = fields.Integer(readonly=True)
    next_num = fields.Integer(compute="_compute_next_num")

    @api.depends('max', 'available')
    def _compute_next_num(self):
        for record in self:
            record.next_num = int(record.max) - record.available + 1

    def pop_number(self):
        """ Consume the availability of a specific range to generate the eTax number for an invoice"""
        self.ensure_one()

        popped = self.next_num
        self.available -= 1

        return popped

    @api.model
    def push_number(self, company_id, number):
        """ Restoring the eTax number that got released after doing reset eFaktur on an invoice so
        that it can be reused

        :param company_id (int): company ID
        :param number (str): number to be restored
        """
        number_int = int(number)
        efaktur_range = self.search([('company_id', '=', company_id), ('min', '<=', number), ('max', '>=', number)], limit=1)

        # if the released number is the last popped number from the range, we simply extend the availability
        if efaktur_range.next_num == int(number) + 1:
            efaktur_range.available += 1
            return

        # if the released number is not the last used number from any range, find the range it belongs and split it
        # i.e range: 1 - 10, available=5, next_number=6, release 3
        # split 1-10 to 1-3 available=1 AND 4-10 available=5
        if efaktur_range:
            if efaktur_range.min == efaktur_range.max:
                efaktur_range.available += 1
            else:
                maximum = efaktur_range.max
                available = efaktur_range.available
                efaktur_range.write({
                    'available': 1,
                    'max': '%013d' % number_int
                })

                self.create({
                    'company_id': company_id,
                    'min': '%013d' % (number_int + 1),
                    'max': maximum,
                    'available': available  # keep original available to not change next_num of that range
                })
        else:
            # in older versions, min value of a range increases after being used
            # to handle the case post migration, we will create the range
            # containing only that number instead
            self.create({
                'company_id': company_id,
                'min': '%013d' % number_int,
                'max': '%013d' % number_int,
                'available': 1
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
            # available could be part of vals in case a new range is created
            # due to range being split in two when a number is reset
            if 'available' not in vals:
                vals['available'] = 1 + int(vals['max']) - int(vals['min'])
        return super().create(vals_list)

    def write(self, vals):
        """ Override to determine behaviour of changing min and max of an e-Faktur range

        For unused ranges, availability lowers when minimum is increased or maximum is decreased. Vice versa applies.
        For used ranges, minimum is fixed while maximum can only be udpated to a value above the used number. Availability
        decreases when the maximum is decreased and vice versa.
        """
        diff = 0
        if 'max' in vals and 'available' not in vals:
            # A new max should never be lower than an already used number
            if int(vals['max']) < self.next_num and 'available' not in vals:
                raise ValidationError(_("You are not allowed to change the max to a number lower than already used"))
            diff += int(vals['max']) - int(self.max)
        if 'min' in vals and 'available' not in vals:
            # A new min cannot be set on a used range
            if self.next_num > int(self.min):
                raise ValidationError(_("You are not allowed to change the min of a range that is already in use"))
            # if range was unused, adapt it according to how min is changed
            if int(self.min) == self.next_num:
                diff += int(self.min) - int(vals['min'])
        if diff:
            vals['available'] = self.available + diff
        return super().write(vals)

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

    @api.depends('min', 'max')
    def _compute_display_name(self):
        for efaktur in self:
            efaktur.display_name = "%s - %s" % (efaktur.min, efaktur.max)

    @api.ondelete(at_uninstall=False)
    def _unlink_except_used_ranges(self):
        """ Only allow deletion on ranges that is unused"""
        if any(efaktur_range.next_num > int(efaktur_range.min) for efaktur_range in self):
            raise UserError(_("You can not delete eFaktur range that has been used to generate an eTax number"))
