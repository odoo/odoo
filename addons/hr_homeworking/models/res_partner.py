from odoo import models
from odoo.libs.debug_log import DebugLog

from .hr_homeworking import PLAIN_IM_STATUSES

_debug = DebugLog(__name__)


class ResPartner(models.Model):
    _inherit = "res.partner"

    def _compute_presence(self):
        super()._compute_presence()
        users = self.user_ids
        locations = users.employee_id.sudo()._get_today_location()
        employee_by_partner = {
            user.partner_id.id: user.employee_id.id for user in users
        }
        for partner in self:
            location = locations.get(employee_by_partner.get(partner.id))
            if not location or partner.im_status not in PLAIN_IM_STATUSES:
                continue
            _debug.logic(
                "presence.located",
                partner=partner,
                status=partner.im_status,
                location_type=location.location_type,
            )
            partner.im_status = f"{location.location_type}_{partner.im_status}"
