from odoo import models, fields 


class EstateProperty(models.Model):
    _inherit = "estate.property"

    def sell_property(self):
        res = super().sell_property()

        for record in self:
               self.env["account_move"].create({
                    "partner_id": record.buyer_id.id,
                    "move_type" : "out_invoice",
                    "invoice_line_ids": [
                         fields.command.create({
                              "name": "6'%' comission",
                              "quantity": 1,
                              "price_unit": record.selling_price * 0.06,
                         }),
                         fields.command.create({
                              "name": "Administrative Fees",
                              "quantity": 1,
                              "price_unit": 100.0,
                         }),
                    ],
               })