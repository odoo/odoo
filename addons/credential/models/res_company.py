from odoo import fields, models


class ResCompany(models.Model):
    _name = "res.company"
    _inherit = ["res.company", "mixin.credential.holder"]
    _credential_holder_field = "company_credential_id"
    _credential_purpose = "company:settings"

    company_credential_id = fields.Many2one(
        comodel_name="credential.credential",
        string="Credential",
        copy=False,
        ondelete="restrict",
        groups="base.group_system",
        help="Holds the secrets this company's integrations keep.",
    )

    def _credential_company_id(self):
        self.check_singleton()
        return self.id
