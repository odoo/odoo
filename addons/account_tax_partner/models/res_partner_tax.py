# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, fields


class ResPartnerTax(models.Model):
    _name = "res.partner.tax"
    _description = "res.partner.tax"
    _check_company_auto = True
    _order = "to_date desc, from_date desc, tax_id, company_id"

    partner_id = fields.Many2one('res.partner', required=True, ondelete='cascade')
    tax_id = fields.Many2one('account.tax', required=True, change_default=True,)
    company_id = fields.Many2one('res.company', related='tax_id.company_id', store=True,)
    from_date = fields.Date()
    to_date = fields.Date()
    amount = fields.Float(required=True, digits=(16, 4))
