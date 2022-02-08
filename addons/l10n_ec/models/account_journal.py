from odoo import fields, models


class AccountJournal(models.Model):

    _inherit = "account.journal"

    l10n_ec_entity = fields.Char(string="Emission Entity", size=3, default="001")
    l10n_ec_emission = fields.Char(string="Emission Point", size=3, default="001")
    l10n_ec_emission_address_id = fields.Many2one(
        comodel_name="res.partner",
        string="Emission address",
        domain="['|', ('id', '=', company_partner_id), '&', ('id', 'child_of', company_partner_id), ('type', '!=', 'contact')]",
    )

    l10n_ec_emission_type = fields.Selection(
        string="Emission type",
        selection=[
            ("pre_printed", "Pre Printed"),
            ("auto_printer", "Auto Printer"),
            ("electronic", "Electronic"),
        ],
        default="electronic",
    )
