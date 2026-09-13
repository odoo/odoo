from odoo import _, api, fields, models


class AccountFiscalPosition(models.Model):
    _inherit = "account.fiscal.position"

    l10n_ar_afip_responsibility_type_ids = fields.Many2many(
        comodel_name="l10n_ar.afip.responsibility.type",
        relation="l10n_ar_afip_reponsibility_type_fiscal_pos_rel",
        string="ARCA Responsibility Types",
        help="List of ARCA responsibilities where this fiscal position "
        "should be auto-detected",
    )

    def _get_fpos_validation_functions(self, partner, company=None):
        functions = super()._get_fpos_validation_functions(partner, company=company)
        company = company or self.env.company
        if company.country_id.code != "AR":
            return functions
        return [
            # `not ... or` on purpose, matching every other validation function:
            # the responsibility list is a *restriction*, so a fiscal position
            # that declares none is unrestricted. Without the guard no such
            # position can ever auto-apply in an AR company — which silently
            # included l10n_ar_domestic_fiscal_position, the one the chart
            # template ships and expects to be picked for domestic customers.
            lambda fpos: (
                not fpos.l10n_ar_afip_responsibility_type_ids
                or partner.l10n_ar_afip_responsibility_type_id
                in fpos.l10n_ar_afip_responsibility_type_ids
            ),
        ] + functions
