from odoo import _, fields, models


class ResPartner(models.Model):
    _inherit = "res.partner"

    l10n_it_edi_doi_ids = fields.One2many(
        comodel_name="l10n_it_edi_doi.declaration_of_intent",
        inverse_name="partner_id",
        string="Available Declarations of Intent of this partner",
        domain=lambda self: [("company_id", "=", self.env.company.id)],
    )

    def l10n_it_edi_doi_action_view_declarations(self):
        self.check_singleton()
        return {
            "name": _("Declaration of Intent of %s", self.display_name),
            "type": "ir.actions.act_window",
            "res_model": "l10n_it_edi_doi.declaration_of_intent",
            "domain": [("partner_id", "=", self.commercial_partner_id.id)],
            "views": [
                (self.env.ref("l10n_it_edi_doi.view_l10n_it_edi_doi_tree").id, "list"),
                (self.env.ref("l10n_it_edi_doi.view_l10n_it_edi_doi_form").id, "form"),
            ],
            "context": {
                "default_partner_id": self.id,
            },
        }
