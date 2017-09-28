from odoo import api, models


class ResUsers(models.Model):
    _inherit = "res.users"

    @api.model
    def check_credentials(self, password):
        """Make all this session's wishlists belong to its owner user."""
        result = super(ResUsers, self).check_credentials(password)
        self.env["product.wishlist"]._join_current_user_and_session()
        return result
