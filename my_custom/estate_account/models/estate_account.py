from odoo import Command, models, fields


class EstateCount(models.Model): 
    _inherit = "estate.property"

    def action_sold(self):
        result = super().action_sold() #có thể không cần biến lưu, lưu để phòng tránhtránh

        self.env["account.move"].create({
            "partner_id": self.buyer_id.id,
            "move_type": "out_invoice",  # Hóa đơn bán hàng không nhận tiền ngay
            # entry, out_refund(hóa đơn giảm giá từ cty), in_invoice (hóa đơn mua hàng không nhận tiền ngay)
            # in_refund(hóa đơn giảm giá cho cty)
            #out_receipt (hóa đơn bán hàng, nhận tiền ngay)
            #in_receipt (hóa đơn mua hàng, trả tiền ngay)
            "journal_id": self.env["account.journal"].search([("type", "=", "sale")], limit=1).id, #nhật kí loại doanh thu(sale), purchase, cash, bank, general
            # có nhiều journal (vd sale thì có online và retail,...,.)
            "invoice_date": fields.Date.today(),
            "invoice_line_ids": [
                Command.create({
                    "name": self.name,
                    "quantity": 1,
                    "price_unit": self.selling_price * 0.06
                }),
                Command.create({
                    "name": self.name,
                    "quantity": 1,
                    "price_unit": 100,
                })
            ]
        })

        return result
