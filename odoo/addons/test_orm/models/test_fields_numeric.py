from odoo import api, fields, models


class ResPartner(models.Model):
    """User inherits partner, so we are implicitly adding these fields to User
       This essentially reproduces the (sad) situation introduced by account.
    """
    _inherit = 'res.partner'

    currency_id = fields.Many2one('res.currency', compute='_get_company_currency', readonly=True)
    monetary = fields.Monetary()  # implicitly depends on currency_id as currency_field

    def _get_company_currency(self):
        for partner in self:
            partner.currency_id = partner.sudo().company_id.currency_id
