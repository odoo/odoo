# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import api, fields, models
from odoo.osv import expression


class CompanyActivities(models.Model):
    _description = 'SII Company Economical Activities'
    _name = 'l10n_cl.company.activities'
    _rec_names_search = ['name', 'code']

    code = fields.Char('Activity Code', required=True)
    name = fields.Char('Complete Name', required=True)
    tax_category = fields.Selection([
        ('1', '1'),
        ('2', '2'),
        ('nd', 'ND')
    ], 'TAX Category', default='1', help='If your company is 2nd category tax payer type, you should use activity '
                                         'codes of type 2, otherwise they should be type 1. '
                                         'If your activity is affected by vat tax depending on other situations, '
                                         'SII uses type ND. In every cases the tax category is defined by the CIIU4.CL '
                                         'nomenclature adopted by SII, and you should only add new activities in case '
                                         'they are added in the future.')
    active = fields.Boolean('Active', help='Allows you to hide the activity without removing it.', default=True)

    @api.depends('code')
    def _compute_display_name(self):
        for record in self:
            record.display_name = f'({record.code}) {record.name}'
