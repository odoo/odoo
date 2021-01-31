# ©  2015-2019 Deltatech
# See README.rst file on addons root folder for license details


from odoo import _, api, models
from odoo.exceptions import UserError


class StockQuant(models.Model):
    _inherit = "stock.quant"

    @api.model
    def _update_available_quantity(
        self, product_id, location_id, quantity, lot_id=None, package_id=None, owner_id=None, in_date=None
    ):

        if location_id.usage == "internal" and (product_id.qty_available + quantity) < 0:
            if location_id.company_id.no_negative_stock:
                raise UserError(
                    _(
                        "You have chosen to avoid negative stock. \
                        %s pieces of %s are remaining in location %s  but you want to transfer  \
                        %s pieces. Please adjust your quantities or \
                        correct your stock with an inventory adjustment."
                    )
                    % (product_id.qty_available, product_id.name, location_id.name, quantity)
                )

        return super(StockQuant, self)._update_available_quantity(
            product_id, location_id, quantity, lot_id, package_id, owner_id, in_date
        )
