import logging

from odoo import _, api, fields, models
from odoo.exceptions import ValidationError

# from dateutil.relativedelta import relativedelta
_logger = logging.getLogger(__name__)


class L10n_ArPartnerTax(models.Model):
    _name = "l10n_ar.partner.tax"
    _description = "Argentinean Partner Taxes"
    _order = "to_date desc, from_date desc, tax_id"
    _check_company_auto = True
    # The company of this model is `company_ids`, related from the tax, so the
    # plural contract is the one that matches it. The singular helper emitted
    # `company_id` against a model that declares no such field.
    _check_company_domain = models.check_companies_domain_parent_of

    partner_id = fields.Many2one(
        comodel_name="res.partner",
        required=True,
        ondelete="cascade",
        check_company=True,
    )
    tax_id = fields.Many2one(
        comodel_name="account.tax",
        required=True,
    )
    company_ids = fields.Many2many(related="tax_id.company_ids")
    from_date = fields.Date()
    to_date = fields.Date()
    ref = fields.Char(string="ref")

    @api.constrains("from_date", "to_date")
    def check_partner_tax_dates(self):
        if self.filtered(
            lambda x: x.from_date and x.to_date and x.from_date >= x.to_date
        ):
            raise ValidationError(
                _('"From date" must be lower than "To date" on Withholding (AR) taxes.')
            )
