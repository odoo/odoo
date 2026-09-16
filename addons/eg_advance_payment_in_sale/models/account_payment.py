from odoo import models, fields, api, _


class AccountPayment(models.Model):
    _inherit = "account.payment"

    sale_id = fields.Many2one(comodel_name="sale.order", string="Sale Order")

    @api.model
    def create(self, vals):
        res = super(AccountPayment, self).create(vals)
        if 'ref' in vals:
            sale_id = self.env["sale.order"].search([("name", "=", vals['ref'])], limit=1)
            if sale_id and not res.sale_id:
                res.sale_id = sale_id.id
            invoice_id = self.env["account.move"].search([("name", "=", vals['ref'])], limit=1)
            if invoice_id and not res.sale_id:
                sale_id = self.env["sale.order"].search([("name", "=", invoice_id.origin)], limit=1)
                if sale_id:
                    res.sale_id = sale_id.id
        return res