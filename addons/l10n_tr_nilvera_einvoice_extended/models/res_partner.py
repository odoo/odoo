from odoo import fields, models


class ResPartner(models.Model):
    _inherit = "res.partner"

    l10n_tr_tax_office_id = fields.Many2one(
        "l10n_tr.res.tax.office", string="Tax Office"
    )

    def _compute_display_name(self):
        super()._compute_display_name()
        for partner in self.filtered(lambda r: r._context.get("show_vat")):
            if partner._context.get("show_vat") and partner.l10n_tr_tax_office_id:
                partner.display_name = (
                    f"{partner.display_name}\n{partner.l10n_tr_tax_office_id.name}"
                )
