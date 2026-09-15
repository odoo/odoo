from odoo.http import request
from odoo.libs.debug_log import DebugLog

from odoo.addons.mass_mailing.controllers import main

_debug = DebugLog(__name__)


class MassMailController(main.MassMailController):
    def _get_value(self, subscription_type):
        value = super()._get_value(subscription_type)
        if not value and subscription_type == "mobile":
            if not request.env.user._is_public():
                value = request.env.user.partner_id.phone_ids._primary("mobile").number
            elif request.session.get("mass_mailing_phone_ids"):
                value = request.session["mass_mailing_phone_ids"]
            _debug.logic(
                "sms_subscription_value",
                public=request.env.user._is_public(),
                resolved=bool(value),
            )
        return value

    def _get_fname(self, subscription_type):
        value_field = super()._get_fname(subscription_type)
        if not value_field and subscription_type == "mobile":
            _debug.logic("sms_subscription_field_defaulted", field="phone_ids")
            value_field = "phone_ids"
        return value_field
