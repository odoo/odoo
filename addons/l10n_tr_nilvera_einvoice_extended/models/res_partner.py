from odoo import fields, models


class ResPartner(models.Model):
    _inherit = "res.partner"

    l10n_tr_tax_office_id = fields.Many2one(
        "l10n_tr.res.tax.office", string="Tax Office"
    )

    def _compute_display_name(self):
        if self._context.get("show_vat"):
            return super()._compute_display_name()
        tr_partners_with_tax_office = self.filtered("l10n_tr_tax_office_id")
        for partner in tr_partners_with_tax_office:
            partner.display_name = (
                f"{partner.display_name}\n{partner.l10n_tr_tax_office_id.name}"
            )
        super(ResPartner, self - tr_partners_with_tax_office)._compute_display_name()
