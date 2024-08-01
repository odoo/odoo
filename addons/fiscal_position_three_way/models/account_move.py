from odoo import api, models, _
from odoo.exceptions import ValidationError


class AccountMove(models.Model):
    _inherit = "account.move"

    @api.constrains('line_ids', 'fiscal_position_id', 'company_id')
    def _validate_taxes_country(self):
        """ By playing with the fiscal position in the form view, it is possible to keep taxes on the invoices from
        a different country than the one allowed by the fiscal country or the fiscal position.
        This contrains ensure such account.move cannot be kept, as they could generate inconsistencies in the reports.
        """
        self._compute_tax_country_id()  # We need to ensure this field has been computed, as we use it in our check
        for record in self:
            amls = record.line_ids
            impacted_countries = amls.tax_ids.country_id | amls.tax_line_id.country_id
            if impacted_countries and impacted_countries != record.tax_country_id:
                if record.fiscal_position_id and impacted_countries != record.fiscal_position_id.delivery_country_id:
                    raise ValidationError(_("This entry contains taxes that are not compatible with your fiscal position. Check the country set in fiscal position and in your tax configuration."))
                raise ValidationError(_("This entry contains one or more taxes that are incompatible with your fiscal country. Check company fiscal country in the settings and tax country in taxes configuration."))
