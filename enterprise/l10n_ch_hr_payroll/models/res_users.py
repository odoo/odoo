# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, fields

L10N_CH_PAYROLL_WRITABLE_FIELDS = [
    'l10n_ch_canton',
    'l10n_ch_tax_scale',
    'l10n_ch_church_tax',
    'l10n_ch_sv_as_number',
    'l10n_ch_marital_from',
    'l10n_ch_has_withholding_tax',
    'l10n_ch_residence_category',
    'l10n_ch_religious_denomination',
    'l10n_ch_spouse_sv_as_number',
    'l10n_ch_spouse_work_canton',
    'l10n_ch_spouse_work_start_date',
    'l10n_ch_municipality',
]


class User(models.Model):
    _inherit = ['res.users']

    l10n_ch_canton = fields.Selection(related="employee_ids.l10n_ch_canton", readonly=False)
    l10n_ch_tax_scale = fields.Selection(related="employee_ids.l10n_ch_tax_scale", readonly=False)
    l10n_ch_church_tax = fields.Boolean(related="employee_ids.l10n_ch_church_tax", readonly=False)
    l10n_ch_sv_as_number = fields.Char(related="employee_ids.l10n_ch_sv_as_number", readonly=False)
    l10n_ch_marital_from = fields.Date(related="employee_ids.l10n_ch_marital_from", readonly=False)
    l10n_ch_spouse_sv_as_number = fields.Char(related="employee_ids.l10n_ch_spouse_sv_as_number", readonly=False)
    l10n_ch_has_withholding_tax = fields.Boolean(related="employee_ids.l10n_ch_has_withholding_tax", readonly=False)
    l10n_ch_residence_category = fields.Selection(related="employee_ids.l10n_ch_residence_category", readonly=False)
    l10n_ch_religious_denomination = fields.Selection(related="employee_ids.l10n_ch_religious_denomination", readonly=False)
    l10n_ch_spouse_work_canton = fields.Selection(related="employee_ids.l10n_ch_spouse_work_canton", readonly=False)
    l10n_ch_spouse_work_start_date = fields.Date(related="employee_ids.l10n_ch_spouse_work_start_date", readonly=False)
    l10n_ch_municipality = fields.Char(related="employee_ids.l10n_ch_municipality", readonly=False)

    @property
    def SELF_READABLE_FIELDS(self):
        return super().SELF_READABLE_FIELDS + L10N_CH_PAYROLL_WRITABLE_FIELDS

    @property
    def SELF_WRITEABLE_FIELDS(self):
        return super().SELF_WRITEABLE_FIELDS + L10N_CH_PAYROLL_WRITABLE_FIELDS
