from odoo import api, models


class CrmCalendarFilter(models.Model):
    _inherit = "calendar.filters"

    @api.model
    def init_user_filters(self):
        super().init_user_filters()
        if partner_id := self.env.context.get('default_partner_id'):
            self.update_user_filters([{'id': partner_id}])
