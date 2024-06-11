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
    available = fields.Integer(compute='_compute_available', store=True)

    @api.model
    def pop_number(self, company_id):
        range = self.search([('company_id', '=', company_id)], order="min ASC", limit=1)
        if not range:
            return None

        popped = int(range.min)
        if int(range.min) >= int(range.max):
            range.unlink()
        else:
            range.min = '%013d' % (popped + 1)
        return popped

    @api.model
    def push_number(self, company_id, number):
        return self.push_numbers(company_id, number, number)

    @api.model
    def push_numbers(self, company_id, min, max):
        range_sup = self.search([('min', '=', '%013d' % (int(max) + 1))])
        if range_sup:
            range_sup.min = '%013d' % int(min)
            max = range_sup.max

        range_low = self.search([('max', '=', '%013d' % (int(max) - 1))])
        if range_low:
            range_sup.unlink()
            range_low.max = '%013d' % int(max)

        if not range_sup and not range_low:
            self.create({
                'company_id': company_id,
                'max': '%013d' % int(max),
                'min': '%013d' % int(min),
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
            if self.search([
                '&', ('id', '!=', record.id), '|', '|',
                '&', ('min', '<=', record.max), ('max', '>=', record.max),
                '&', ('min', '<=', record.min), ('max', '>=', record.min),
                '&', ('min', '>=', record.min), ('max', '<=', record.max),
            ]):
                raise ValidationError(_('Efaktur interleaving range detected'))

    @api.depends('min', 'max')
    def _compute_available(self):
        for record in self:
            record.available = 1 + int(record.max) - int(record.min)

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
