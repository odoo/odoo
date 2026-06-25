from odoo import models, fields 


class EstateProperty(models.Model):
    _inherit = "estate.property"

    invoice_id = fields.Many2one("account.move", string="Invoice", readonly=True)

    def sell_property(self):
     res = super().sell_property()
     for record in self:
               invoice= self.env["account.move"].create({
                    "partner_id": record.buyer_id.id,
                    "move_type" : "out_invoice",
                    "invoice_line_ids": [
                         fields.Command.create({
                              "name": "6'%' comission",
                              "quantity": 1,
                              "price_unit": record.selling_price * 0.06,
                         }),
                         fields.Command.create({
                              "name": "Administrative Fees",
                              "quantity": 1,
                              "price_unit": 100.0,
                         }),
                    ],
               })
     record_invoice_id = invoice.id
     return res
    

    def view_invoice(self):
         self.ensure.one()
         return self.invoice_id.get_formview_action()

     #     return{
     #          "type": "ir.actions.act_window",
     #          "name":"Invoice",
     #          "res_model": "account_move",
     #          "res_id": self.invoice_id.id,
     #          "view_mode": "form"
     #     }