from odoo import models


class AccountMoveLine(models.Model):
    _inherit = 'account.move.line'

    def _check_edi_line_tax_required(self):
        # EXTENDS account
        for pos_order in (self.move_id.pos_order_ids or []):
            config_id = pos_order.config_id
            if config_id.iface_tipproduct and self.product_id == config_id.tip_product_id:
                # POS tips are enabled and this line's product is the tip product
                return False

        return super()._check_edi_line_tax_required()
