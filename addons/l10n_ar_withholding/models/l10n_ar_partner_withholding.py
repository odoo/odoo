from odoo import models, fields, api
import logging
# from dateutil.relativedelta import relativedelta
_logger = logging.getLogger(__name__)


class ResPartnerArbaAlicuot(models.Model):
    # TODO rename model to res.partner.tax or similar
    _name = "res.partner.arba_alicuot"
    _description = "res.partner.arba_alicuot"
    _order = "to_date desc, from_date desc, tax_id"

    _sql_constraints = [
        ('tax_date_uniq', 'unique(partner_id, tax_id, from_date, to_date)', 'The combination of Tax, Date from and to Date must be unique.')
    ]

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
        'res.company',
        required=True,
        ondelete='cascade',
        default=lambda self: self.env.company,
    )
    from_date = fields.Date(
    )
    to_date = fields.Date(
    )
    ref = fields.Char(
    )
