# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models, api


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    _transaction_code_domain = '''
        [('type', '=', 'transaction'),
        '|', ('expiry_date', '>', context_today().strftime('%Y-%m-%d')), ('expiry_date', '=', None),
        '|', ('start_date', '<', context_today().strftime('%Y-%m-%d')), ('start_date', '=', None)]
    '''

    company_country_id = fields.Many2one(
        'res.country', string="Company country", readonly=True,
        related='company_id.account_fiscal_country_id'
    )
    intrastat_default_invoice_transaction_code_id = fields.Many2one(
        'account.intrastat.code',
        string='Default invoice transaction code',
        related='company_id.intrastat_default_invoice_transaction_code_id',
        domain=_transaction_code_domain,
        readonly=False,
    )
    intrastat_default_refund_transaction_code_id = fields.Many2one(
        'account.intrastat.code',
        string='Default refund transaction code',
        related='company_id.intrastat_default_refund_transaction_code_id',
        domain=_transaction_code_domain,
        readonly=False,
    )
    intrastat_region_id = fields.Many2one(
        comodel_name='account.intrastat.code',
        string='Intrastat region',
        related='company_id.intrastat_region_id',
        domain="[('type', '=', 'region'), '|', ('country_id', '=', False), ('country_id', '=', company_country_id)]",
        readonly=False,
    )
    has_country_regions = fields.Boolean(compute="_compute_has_country_regions")

    @api.depends('intrastat_region_id')
    def _compute_has_country_regions(self):
        regions_without_country = self.env['account.intrastat.code'].search_count(
            domain=[('type', '=', 'region'), ('country_id', '=', False)],
            limit=1,
        )
        regions_counts_groupby_country = {
            intrastat_regions['country_id'][0]: intrastat_regions['country_id_count']
            for intrastat_regions in self.env['account.intrastat.code'].read_group(
                domain=[('type', '=', 'region'), ('country_id', '!=', False)],
                fields=['id:count'],
                groupby=['country_id'],
            )
        }

        for record in self:
            record.has_country_regions = regions_without_country or regions_counts_groupby_country.get(record.company_country_id.id)
