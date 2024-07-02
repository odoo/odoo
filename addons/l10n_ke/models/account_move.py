from odoo import models, fields


class AccountMove(models.Model):
    _inherit = 'account.move'

    wh_certificate_number = fields.Char(
        string='Withholding Certificate Number',
        help='Customer withholding certificate number',
    )

    wh_certificate_date = fields.Date(
        string='Date of Certificate',
    )
