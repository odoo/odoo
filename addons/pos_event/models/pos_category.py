from odoo import models, api, _
from odoo.addons import point_of_sale
from odoo.exceptions import UserError


class PosCategory(models.Model, point_of_sale.PosCategory):

    @api.ondelete(at_uninstall=False)
    def _unlink_except_pos_event_category(self):
        for category in self.ids:
            if category == self.env.ref("pos_event.pos_category_event").id:
                raise UserError(_("Deleting this category is not allowed."))
