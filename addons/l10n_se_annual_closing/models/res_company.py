# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import api, fields, models

from .l10n_se_sru_mapping import SRU_TYPE_BY_TEMPLATE, SRU_TYPES


class ResCompany(models.Model):
    _inherit = 'res.company'

    l10n_se_sru_type = fields.Selection(
        SRU_TYPES,
        string='SRU Form',
        compute='_compute_l10n_se_sru_type',
        store=True,
        readonly=False,
        help="Income tax return form used for the SRU file. Defaults from the chart of "
             "accounts; INK3 (non-profit associations, foundations) must be chosen manually.",
    )

    l10n_se_f_tax_approved = fields.Boolean(
        string='Approved for F-tax',
        help="The company is approved for F-tax. Customer invoices then state it, so the buyer "
             "does not have to withhold preliminary tax.",
    )

    @api.depends('chart_template')
    def _compute_l10n_se_sru_type(self):
        for company in self:
            company.l10n_se_sru_type = SRU_TYPE_BY_TEMPLATE.get(company.chart_template) or company.l10n_se_sru_type or False
