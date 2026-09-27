from odoo import api, fields, models


class ResPartner(models.Model):
    _inherit = 'res.partner'

    l10n_tr_tax_office_id = fields.Many2one(
        comodel_name="l10n_tr.tax.office",
        string="Turkish Tax Office",
        help="Specifies the official Turkish Tax Office where this partner is registered. "
        "This is required for generating valid e-Invoices for this partner.",
    )

    def _compute_available_additional_identifiers_metadata(self):
        # Turkey relies on its own national identifiers (Mersis, Trade Registry, Branch...);
        # keep only the Turkish ones and drop the globally-available identifiers (e.g. DUNS).
        super()._compute_available_additional_identifiers_metadata()
        for partner in self:
            metadata = partner.available_additional_identifiers_metadata
            if partner.country_code == 'TR' and metadata:
                partner.available_additional_identifiers_metadata = {
                    key: vals for key, vals in metadata.items()
                    if 'TR' in (vals.get('countries') or [])
                }

    @api.depends("l10n_tr_tax_office_id")
    def _compute_display_name(self):
        super()._compute_display_name()
        if not self.env.context.get("show_address"):
            return
        tr_partners_with_tax_office = self.filtered("l10n_tr_tax_office_id")
        for partner in tr_partners_with_tax_office:
            if not partner.env.context.get("formatted_display_name"):
                partner.display_name = (
                    f"{partner.display_name}\n{partner.l10n_tr_tax_office_id.name}"
                )

    def _get_tax_office_missing_message(self):
        self.ensure_one()
        return (
            self.env._("The Turkish Tax Office field must be filled")
            if not self.l10n_tr_tax_office_id
            else None
        )

    def _get_tax_office_name(self):
        self.ensure_one()
        return self.l10n_tr_tax_office_id.name
