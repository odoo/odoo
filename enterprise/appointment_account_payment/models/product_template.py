from odoo import api, _, models
from odoo.exceptions import UserError


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    @api.ondelete(at_uninstall=False)
    def _unlink_except_booking_fee_product_template(self):
        default_booking_product = self.env.ref(
            'appointment_account_payment.default_booking_product',
            raise_if_not_found=False
        )
        if default_booking_product and default_booking_product.sudo().product_tmpl_id in self:
            raise UserError(_("You cannot delete the default booking product"))
