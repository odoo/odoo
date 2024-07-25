from odoo import models, fields, api
from odoo.exceptions import ValidationError
import logging
# from dateutil.relativedelta import relativedelta
_logger = logging.getLogger(__name__)


class L10nArPartnerTax(models.Model):
    _name = "l10n_ar.partner.tax"
    _description = "Argentinean Partner Taxes"
    _order = "to_date desc, from_date desc, tax_id"

    partner_id = fields.Many2one(
        'res.partner',
        required=True,
        ondelete='cascade',
    )
    tax_id = fields.Many2one(
        'account.tax',
        # domain=[('applicability', '=', 'taxes')],
        required=True,
        # change_default=True,
    )
    company_id = fields.Many2one(
        related='tax_id.company_id', store=True,
    )
    from_date = fields.Date(
    )
    to_date = fields.Date(
    )
    ref = fields.Char(
    )

    # @api.constrains('partner_id', 'tax_id', 'from_date', 'to_date')
    # def _avoid_repeated_aliquots(self):
    #     for arba_alicuot in self.l10n_ar_tax_ids:
    #         if arba_alicuot.from_date and arba_alicuot.to_date and arba_alicuot.from_date > arba_alicuot.to_date:
    #                 raise ValidationError('The start date cannot be after the end date.')
    #         existing_alicuot = self.l10n_ar_tax_ids.search([
    #             ('tax_id', '=', arba_alicuot.tax_id.id),
    #             ('to_date',  '>=', arba_alicuot.from_date or arba_alicuot.to_date),
    #             ('from_date', '<=', arba_alicuot.to_date or arba_alicuot.from_date),
    #             ('id', '!=', arba_alicuot.id)
    #         ])
    #         if existing_alicuot:
    #             raise ValidationError('The date range overlaps with an existing record for the same tax.')
