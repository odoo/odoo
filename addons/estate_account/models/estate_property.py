# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import Command, models

COMMISSION_RATE = 0.06
ADMINISTRATIVE_FEES = 100.0


class EstateProperty(models.Model):
    _inherit = "estate.property"

    def action_sold(self):
        """Mark the properties as sold, then invoice each buyer the agency's fees."""
        # super() first: if the sale is refused (e.g. no accepted offer), no invoice is created
        res = super().action_sold()
        # Salespeople usually have no invoicing rights, hence sudo(). It is safe here: super() just
        # wrote the properties' state, which raises if the user is not allowed to sell them
        self.env["account.move"].sudo().create([
            {
                # Customer invoice; the default sales journal of the company is used
                "move_type": "out_invoice",
                "partner_id": estate_property.partner_id.id,
                # Command.create(vals) creates a new line linked to the invoice being created
                "invoice_line_ids": [
                    Command.create({
                        "name": self.env._(
                            "Commission on the sale of %(property)s", property=estate_property.name
                        ),
                        "quantity": 1,
                        "price_unit": estate_property.selling_price * COMMISSION_RATE,
                    }),
                    Command.create({
                        "name": self.env._("Administrative fees"),
                        "quantity": 1,
                        "price_unit": ADMINISTRATIVE_FEES,
                    }),
                ],
            }
            for estate_property in self
        ])
        return res
