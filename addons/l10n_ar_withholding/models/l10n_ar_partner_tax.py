from odoo import models, fields, api, _
import datetime
from odoo.exceptions import ValidationError
import logging
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

    @api.constrains('partner_id', 'tax_id', 'from_date', 'to_date')
    def _check_tax_group_overlap(self):
        """
        Constraint method to ensure there is no overlap of taxes from the same tax group
        for the same partner within the specified date range. If such a conflict
        is found, a `ValidationError` is raised.
        """
        for record in self:
            domain = [
                ('id', '!=', record.id),
                ('partner_id', '=', record.partner_id.id),
                ('tax_id.tax_group_id', '=', record.tax_id.tax_group_id.id),
                '&',
                '|', ('from_date', '=', False), ('from_date', '<=', record.to_date or datetime.date.max),
                '|', ('to_date', '=', False), ('to_date', '>=', record.from_date or datetime.date.min),
            ]
            conflicting_records = self.search(domain)
            if conflicting_records:
                raise ValidationError(_(
                    "There cannot be two taxes from the same group in force at the same time for the same company. "
                    "Maybe there is a tax that needs 'To Date' to be set. More information:\n"
                    "* Tax: %(tax_name)s\n"
                    "* To Date: %(date)s\n"
                    "* From Date: %(from_date)s\n"
                    "* Other Taxes: %(other_taxes)s\n",
                    tax_name=record.tax_id.name,
                    date=record.to_date,
                    from_date=record.from_date,
                    other_taxes=conflicting_records.mapped('tax_id.name')
                ))
