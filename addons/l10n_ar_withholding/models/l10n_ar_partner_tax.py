from odoo import models, fields, api, _
from odoo.exceptions import ValidationError
import logging
# from dateutil.relativedelta import relativedelta
_logger = logging.getLogger(__name__)


class L10n_ArPartnerTax(models.Model):
    _name = 'l10n_ar.partner.tax'
    _description = "Argentinean Partner Taxes"
    _order = "to_date desc, from_date desc, tax_id"
    _check_company_auto = True
    _check_company_domain = models.check_company_domain_parent_of

    partner_id = fields.Many2one(
        'res.partner',
        required=True,
        ondelete='cascade',
        check_company=True,
    )
    tax_id = fields.Many2one(
        'account.tax',
        required=True,
    )
    company_id = fields.Many2one(
        related='tax_id.company_id', store=True,
    )
    from_date = fields.Date(
        string="From Date"
    )
    to_date = fields.Date(
        string="To Date"
    )
    ref = fields.Char(
        string="ref"
    )

    @api.constrains('from_date', 'to_date')
    def check_partner_tax_dates(self):
        if self.filtered(lambda x: x.from_date and x.to_date and x.from_date >= x.to_date):
            raise ValidationError(_('"From date" must be lower than "To date" on Withholding (AR) taxes.'))
