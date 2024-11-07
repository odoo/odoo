import re
from odoo import _, api, models, fields


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    l10n_in_hsn_code = fields.Char(string="HSN/SAC Code", help="Harmonized System Nomenclature/Services Accounting Code")
    l10n_in_hsn_warning = fields.Text(string="HSC/SAC warning", compute="_compute_l10n_in_hsn_warning")
    l10n_in_is_gst_registered_enabled = fields.Boolean(compute="_compute_l10n_in_is_gst_registered_enabled")

    @api.depends('company_id.l10n_in_is_gst_registered')
    @api.depends_context('allowed_company_ids')
    def _compute_l10n_in_is_gst_registered_enabled(self):
        for record in self:
            allowed_companies = record.company_id or self.env.companies
            record.l10n_in_is_gst_registered_enabled = any(
                company.l10n_in_is_gst_registered
                for company in allowed_companies
            )

    @api.depends('sale_ok', 'l10n_in_hsn_code')
    def _compute_l10n_in_hsn_warning(self):
        digit_suffixes = {
            '4': _("either 4, 6 or 8"),
            '6': _("either 6 or 8"),
            '8': _("8")
        }
        active_hsn_code_digit_len = max(
            int(company.l10n_in_hsn_code_digit)
            for company in self.env.companies
        )
        for record in self:
            check_hsn = record.sale_ok and record.l10n_in_hsn_code and active_hsn_code_digit_len
            if check_hsn and (not re.match(r'^\d{4}$|^\d{6}$|^\d{8}$', record.l10n_in_hsn_code) or len(record.l10n_in_hsn_code) < active_hsn_code_digit_len):
                record.l10n_in_hsn_warning = _(
                    "HSN code field must consist solely of digits and be %s in length.",
                    digit_suffixes.get(str(active_hsn_code_digit_len))
                )
                continue
            record.l10n_in_hsn_warning = False
