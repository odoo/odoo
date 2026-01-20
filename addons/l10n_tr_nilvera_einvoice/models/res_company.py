from dateutil.relativedelta import relativedelta

from odoo import fields, models


class ResCompany(models.Model):
    _inherit = "res.company"

    l10n_tr_earchive_sale_last_fetched_date = fields.Datetime(
        default=lambda s: fields.Datetime.now() - relativedelta(months=1)
    )
    l10n_tr_einvoice_sale_last_fetched_date = fields.Datetime(
        default=lambda s: fields.Datetime.now() - relativedelta(months=1)
    )
    l10n_tr_einvoice_purchase_last_fetched_date = fields.Datetime(
        default=lambda s: fields.Datetime.now() - relativedelta(months=1)
    )
    l10n_tr_tax_office_id = fields.Many2one(related="partner_id.l10n_tr_tax_office_id", readonly=False)
    l10n_tr_nilvera_export_alias = fields.Char(
        string="Nilvera Export Alias",
        default="urn:mail:ihracatpk@gtb.gov.tr",
        groups="base.group_system",
    )
