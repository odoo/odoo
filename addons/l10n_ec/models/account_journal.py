from odoo import api, fields, models


class AccountJournal(models.Model):
    _inherit = "account.journal"

    l10n_ec_require_emission = fields.Boolean(
        string='Require Emission',
        compute='_compute_l10n_ec_require_emission',
        help='True if an entity and emission point must be set on the journal'
    )
    l10n_ec_entity = fields.Char(string="Emission Entity", size=3, copy=False)
    l10n_ec_emission = fields.Char(string="Emission Point", size=3, copy=False)
    l10n_ec_emission_address_id = fields.Many2one(
        comodel_name="res.partner",
        string="Emission address",
        domain="['|', ('id', '=', company_partner_id), '&', ('id', 'child_of', company_partner_id), ('type', '!=', 'contact')]",
    )

    @api.depends('type', 'country_code', 'l10n_latam_use_documents')
    def _compute_l10n_ec_require_emission(self):
        for journal in self:
            journal.l10n_ec_require_emission = journal.type == 'sale' and journal.country_code == 'EC' and journal.l10n_latam_use_documents

    # NOTE: Removed in master as it has no use
    l10n_ec_emission_type = fields.Selection(
        string="Emission type",
        selection=[
            ("pre_printed", "Pre Printed"),
            ("auto_printer", "Auto Printer"),
            ("electronic", "Electronic"),
        ],
        default="electronic",
    )
