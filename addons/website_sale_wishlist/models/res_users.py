from odoo import api, fields, models
from odoo.http import request


class ResUsers(models.Model):
    _inherit = "res.users"

    current_session = fields.Char(compute="_compute_current_session")

    @api.multi
    def _compute_current_session(self):
        """Know current session for this user."""
        for one in self:
            try:
                one.current_session = request.session.sid
            except (AttributeError, RuntimeError):
                pass  # Unbound session, value is already False, nothing to do

    @api.model
    def check_credentials(self, password):
        """Make all this session's wishlists belong to its owner user."""
        result = super(ResUsers, self).check_credentials(password)
        self.env["product.wishlist"]._join_current_user_and_session()
        return result
