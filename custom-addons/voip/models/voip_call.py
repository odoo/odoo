# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _
from odoo.osv import expression


class VoipCall(models.Model):
    _name = "voip.call"
    _description = """A phone call handled using the VoIP application"""

    phone_number = fields.Char(required=True, readonly=True)
    direction = fields.Selection(
        [
            ("incoming", "Incoming"),
            ("outgoing", "Outgoing"),
        ],
        default="outgoing",
        readonly=True,
    )
    state = fields.Selection(
        [
            ("aborted", "Aborted"),
            ("calling", "Calling"),
            ("missed", "Missed"),
            ("ongoing", "Ongoing"),
            ("rejected", "Rejected"),
            ("terminated", "Terminated"),
        ],
        default="calling",
        index=True,
    )
    end_date = fields.Datetime()
    start_date = fields.Datetime()
    # Since activities are deleted from the database once marked as done, the
    # activity name is saved here in order to be preserved.
    activity_name = fields.Char(help="The name of the activity related to this phone call, if any.")
    partner_id = fields.Many2one("res.partner", "Contact", index=True)
    user_id = fields.Many2one("res.users", "Responsible", default=lambda self: self.env.uid, index=True)

    @api.depends("state", "partner_id.name")
    def _compute_display_name(self):
        def get_name(call):
            if call.activity_name:
                return call.activity_name
            if call.state == "aborted":
                return _("Aborted call to %(phone_number)s", phone_number=call.phone_number)
            if call.state == "missed":
                return _("Missed call from %(phone_number)s", phone_number=call.phone_number)
            if call.state == "rejected":
                if call.direction == "incoming":
                    return _("Rejected call from %(phone_number)s", phone_number=call.phone_number)
                return _("Rejected call to %(phone_number)s", phone_number=call.phone_number)
            if call.partner_id:
                if call.direction == "incoming":
                    return _("Call from %(correspondent)s", correspondent=call.partner_id.name)
                return _("Call to %(correspondent)s", correspondent=call.partner_id.name)
            if call.direction == "incoming":
                return _("Call from %(phone_number)s", phone_number=call.phone_number)
            return _("Call to %(phone_number)s", phone_number=call.phone_number)

        for call in self:
            call.display_name = get_name(call)

    @api.model
    def create_and_format(self, res_id: int = None, res_model: str = None, **kwargs) -> list:
        """Creates a call from the provided values and returns it formatted for
        use in JavaScript. If a record is provided via its id and model,
        introspects it for a recipient.
        """
        if res_id and res_model:
            related_record = self.env[res_model].browse(res_id)
            kwargs["partner_id"] = next(
                iter(related_record._mail_get_partners(introspect_fields=True)[related_record.id]),
                self.env["res.partner"],
            ).id
        return self.create(kwargs)._format_calls()

    @api.model
    def get_recent_phone_calls(self, search_terms: str = None, offset: int = 0, limit: int = None) -> list:
        domain = [("user_id", "=", self.env.uid)]
        if search_terms:
            search_fields = ["phone_number", "partner_id.name", "activity_name"]
            search_domain = expression.OR([[(field, "ilike", search_terms)] for field in search_fields])
            domain += search_domain
        return self.search(domain, offset=offset, limit=limit, order="create_date DESC")._format_calls()

    @api.model
    def _get_number_of_missed_calls(self) -> int:
        domain = [("user_id", "=", self.env.uid), ("state", "=", "missed")]
        last_seen_phone_call = self.env.user.last_seen_phone_call
        if last_seen_phone_call:
            domain += [("id", ">", last_seen_phone_call.id)]
        return self.search_count(domain)

    def abort_call(self) -> list:
        self.state = "aborted"
        return self._format_calls()

    def start_call(self) -> list:
        self.start_date = fields.Datetime.now()
        self.state = "ongoing"
        return self._format_calls()

    def end_call(self, activity_name: str = None) -> list:
        self.end_date = fields.Datetime.now()
        self.state = "terminated"
        if activity_name:
            self.activity_name = activity_name
        return self._format_calls()

    def reject_call(self) -> list:
        self.state = "rejected"
        return self._format_calls()

    def miss_call(self) -> list:
        self.state = "missed"
        return self._format_calls()

    def get_contact_info(self):
        self.ensure_one()
        number = self.phone_number
        # Internal extensions could theoretically be one or two digits long.
        # phone_mobile_search doesn't handle numbers that short: do a regular
        # search for the exact match:
        if len(number) < 3:
            domain = ["|", ("phone", "=", number), ("mobile", "=", number)]
        # 00 and + both denote an international prefix. phone_mobile_search will
        # match both indifferently.
        elif number.startswith(("+", "00")):
            domain = [("phone_mobile_search", "=", number)]
        # USA: Calls between different area codes are usually prefixed with 1.
        # Conveniently, the country code for the USA also happens to be 1, so we
        # just need to add the + symbol to format it like an international call
        # and match what's supposed to be stored in the database.
        elif number.startswith("1"):
            domain = [("phone_mobile_search", "=", f"+{number}")]
        # 0 is the national prefix recommended by the ITU-T. This means that a
        # number starting with 0 will identify a national call in most
        # countries. We don't know the country code, so we can't convert the
        # number to the international format: Replace the prefix with a
        # wildcard.
        elif number.startswith("0"):
            domain = [("phone_mobile_search", "=like", f"%{number[1:]}")]
        # The phone number doesn't match any expected format. Could it be some
        # kind of internal extension? Try looking for an exact match:
        else:
            domain = [("phone_mobile_search", "=", number)]
        partner = self.env["res.partner"].search(domain, limit=1)
        if not partner:
            return False
        self.partner_id = partner
        return self.partner_id._format_contacts()[0]

    def _format_calls(self) -> list:
        return [
            {
                "id": call.id,
                "creationDate": call.create_date,
                "direction": call.direction,
                "displayName": call.display_name,
                "endDate": call.end_date,
                "partner": call.partner_id._format_contacts()[0] if call.partner_id else False,
                "phoneNumber": call.phone_number,
                "startDate": call.start_date,
                "state": call.state,
            }
            for call in self
        ]
