from odoo import api, fields, models


class ResPartner(models.Model):
    _inherit = "res.partner"

    l10n_tr_tax_office_id = fields.Many2one(
        "l10n_tr.res.tax.office", string="Turkish Tax Office"
    )

    @api.depends('l10n_tr_tax_office_id')
    def _compute_display_name(self):
        if not self._context.get("show_address"):
            return super()._compute_display_name()
        super()._compute_display_name()
        tr_partners_with_tax_office = self.filtered("l10n_tr_tax_office_id")
        for partner in tr_partners_with_tax_office:
            partner.display_name = (
                f"{partner.display_name}\n{partner.l10n_tr_tax_office_id.name}"
            )
