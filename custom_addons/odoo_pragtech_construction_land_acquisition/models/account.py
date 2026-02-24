# -*- coding: utf-8 -*-

from odoo import models, fields,api, _
from odoo.exceptions import ValidationError



class AccountMove(models.Model):
    """
        USED: Added Field On 'account.move' Model
    """
    _inherit = "account.move"

    is_lease = fields.Boolean('Is Lease')
    is_sale = fields.Boolean('Is Sale')
    proposal_id = fields.Many2one('land.proposal', 'Property')


class AccountMoveLine(models.Model):
    """
        USED: Added Field On 'account.move.line' Model
    """
    _inherit = "account.move.line"

    is_lease = fields.Boolean('Is Lease')
    is_sale = fields.Boolean('Is Sale')
    proposal_id = fields.Many2one('land.proposal', 'Property')
    from_date = fields.Date('From Date')
    to_date = fields.Date('To date')
    unit = fields.Char('Unit')



class ProductTemplate(models.Model):
    _inherit = "product.template"

    proposed_product = fields.Boolean('Proposed Product')

    @api.constrains('proposed_product')
    def _constrains_productss(self):
        for team in self:
            products_val = team.env['product.template'].search(
                [('proposed_product', '=', True)])
            if products_val:
                if len(products_val) > 1:
                    raise ValidationError(_('Already Proposed Product Assign..!!'))
