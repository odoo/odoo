from odoo import api, models


class CrmCalendarFilter(models.Model):
    _inherit = "calendar.filters"

    @api.model
    def init_partner_filters(self):
        super().init_partner_filters()
        if partner_id := self.env.context.get('default_partner_id'):
            self.update_partner_filters([partner_id])
