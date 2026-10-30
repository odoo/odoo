from odoo import api, fields, models

AT_SERIES_SALES_DOCUMENT_TYPES = [
    ('quotation', 'Quotation (OR)'),
    ('sales_order', 'Sales Order (NE)'),
]
# The AT's code for each sales document type: its SAF-T WorkType, and the prefix suggested for its series.
AT_SERIES_WORKING_DOCUMENT_SAFT_TYPE_MAP = {
    'quotation': 'OR',
    'sales_order': 'NE',
}


class L10nPtATSeries(models.Model):
    _inherit = "l10n_pt.at.series"

    document_type = fields.Selection(
        selection_add=AT_SERIES_SALES_DOCUMENT_TYPES,
        ondelete={'quotation': 'cascade', 'sales_order': 'cascade'},
    )
    l10n_pt_offer_sales_order_series = fields.Boolean(compute='_compute_l10n_pt_offer_sales_order_series')
    l10n_pt_create_sales_order_series = fields.Boolean(
        string="Also create the Sales Order series",
        compute='_compute_l10n_pt_create_sales_order_series',
        readonly=False,
        help="Create the Sales Order (NE) series under the same name, so that confirming the "
             "quotation does not stop for a missing series.",
    )

    @api.depends('document_type', 'company_id')
    def _compute_l10n_pt_offer_sales_order_series(self):
        # Offered on a new quotation series when its company has no sales-order series to use yet.
        self.l10n_pt_offer_sales_order_series = False
        new_quotation_series = self.filtered(lambda s: not s.id and s.document_type == 'quotation')
        for company, series in new_quotation_series.grouped('company_id').items():
            series.l10n_pt_offer_sales_order_series = not self.search_count([
                *self._l10n_pt_company_domain(company),
                ('document_type', '=', 'sales_order'),
                ('active', '=', True),
            ], limit=1)

    @api.depends('l10n_pt_offer_sales_order_series')
    def _compute_l10n_pt_create_sales_order_series(self):
        for series in self:
            series.l10n_pt_create_sales_order_series = series.l10n_pt_offer_sales_order_series

    @api.model
    def default_get(self, fields):
        defaults = super().default_get(fields)
        if 'prefix' in fields and not defaults.get('prefix') and (
            prefix := AT_SERIES_WORKING_DOCUMENT_SAFT_TYPE_MAP.get(defaults.get('document_type'))
        ):
            defaults['prefix'] = prefix
        return defaults

    @api.model_create_multi
    def create(self, vals_list):
        create_sales_order_series = [vals.pop('l10n_pt_create_sales_order_series', False) for vals in vals_list]
        records = super().create(vals_list)
        quotation_series = self.browse(
            series.id
            for series, requested in zip(records, create_sales_order_series)
            if requested and series.document_type == 'quotation'
        )
        if quotation_series:
            super().create(quotation_series.copy_data({
                'document_type': 'sales_order',
                'prefix': AT_SERIES_WORKING_DOCUMENT_SAFT_TYPE_MAP['sales_order'],
                'at_code': False,
            }))
        return records
