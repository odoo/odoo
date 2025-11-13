from odoo import fields, models


class ResCompany(models.Model):
    _inherit = "res.company"

    l10n_tr_tax_office_id = fields.Many2one(
        related="partner_id.l10n_tr_tax_office_id",
        readonly=False,
        help="Specifies the official Turkish Tax Office where this partner is registered. "
        "This is required for generating valid e-Invoices for this partner.",
    )
    l10n_tr_nilvera_export_alias = fields.Char(
        string="Nilvera Export Alias",
        default="urn:mail:ihracatpk@gtb.gov.tr",
        groups="base.group_system",
        help="This is the default alias used when sending export invoices. \n"
        "This alias is typically set to the official inbox of the Turkish Ministry of Trade"
        "and should not be changed unless instructed by your integrator. ",
    )
