# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models


class ResCompany(models.Model):
    _inherit = 'res.company'

    def _default_bank_leaves_type(self):
        return self.env['hr.leave.type'].create({
            'name': 'Bank Holidays',
            'validation_type': 'hr', # TODO: See what rights it should have by default
            'company_id': self,
            'allocation_type': 'no',
            'color_name': 'magenta',
        })

    bank_leaves_type_id = fields.Many2one('hr.leave.type', string='Bank Holidays', default=_default_bank_leaves_type,
                                           help="This is the leave that will be used to describe bank holidays")

    @api.model
    def _init_data_hr_holidays(self):
        for company in self.search([('bank_leaves_type_id', '=', False)]):
            company._create_default_bank_leaves_type()

    def _create_default_bank_leaves_type(self):
        self.bank_leaves_type_id = self._default_bank_leaves_type().id
