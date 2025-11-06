from odoo import _, api, fields, models


class ResPartner(models.Model):
    _inherit = "res.partner"

    l10n_tr_tax_office_id = fields.Many2one("l10n_tr_nilvera_einvoice.tax.office", string="Turkish Tax Office")

    @api.depends('l10n_tr_tax_office_id')
    def _compute_display_name(self):
        super()._compute_display_name()
        tr_partners_with_tax_office = self.filtered("l10n_tr_tax_office_id")
        if not self.env.context.get('show_address'):
            return
        for partner in tr_partners_with_tax_office:
            if not partner.env.context.get("formatted_display_name"):
                partner.display_name = (f"{partner.display_name}\n{partner.l10n_tr_tax_office_id.name}")

    def _get_tax_office_missing_message(self):
        # OVERRIDE
        self.ensure_one()
        return _("The Turkish Tax Office field must be filled") if not self.l10n_tr_tax_office_id else None

    def _get_tax_office_for_edispatch(self):
        # OVERRIDE
        self.ensure_one()
        return self.l10n_tr_tax_office_id.name
