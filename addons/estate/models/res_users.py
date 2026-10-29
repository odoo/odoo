# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class ResUsers(models.Model):
    # `_inherit` without `_name` extends the existing model in place: the field is added to the
    # `res.users` model and table defined in `base`, for every addon using users
    _inherit = "res.users"

    # The domain limits the One2many to the properties this user is still selling. The label must
    # differ from the ones of existing res.users fields, such as "Properties" (`properties`)
    property_ids = fields.One2many(
        string="Real Estate Properties",
        comodel_name="estate.property",
        inverse_name="user_id",
        domain=[("state", "in", ("new", "offer_received"))],
    )
