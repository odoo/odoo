from odoo import api, models, fields


class ResUsers(models.Model):
    _inherit = "res.users"

    last_seen_phone_call = fields.Many2one("voip.call")
    # --------------------------------------------------------------------------
    # VoIP User Configuration Fields
    # --------------------------------------------------------------------------
    # These fields mirror those defined in `res.users.settings`. The reason they
    # are not directly defined in here is that we want these fields to have
    # different access rights than the rest of the fields of `res.users`. See
    # their definition in `res.users.settings` for comprehensive documentation.
    # --------------------------------------------------------------------------
    external_device_number = fields.Char(
        compute="_compute_external_device_number",
        inverse="_reflect_change_in_res_users_settings",
        groups="base.group_user",
    )
    how_to_call_on_mobile = fields.Selection(
        [("ask", "Ask"), ("voip", "VoIP"), ("phone", "Device's phone")],
        compute="_compute_how_to_call_on_mobile",
        inverse="_reflect_change_in_res_users_settings",
        groups="base.group_user",
    )
    should_auto_reject_incoming_calls = fields.Boolean(
        compute="_compute_should_auto_reject_incoming_calls",
        inverse="_reflect_change_in_res_users_settings",
        groups="base.group_user",
    )
    should_call_from_another_device = fields.Boolean(
        compute="_compute_should_call_from_another_device",
        inverse="_reflect_change_in_res_users_settings",
        groups="base.group_user",
    )
    voip_provider_id = fields.Many2one(
        "voip.provider",
        compute="_compute_voip_provider_id",
        inverse="_reflect_change_in_res_users_settings",
        groups="base.group_user",
    )
    voip_secret = fields.Char(
        compute="_compute_voip_secret",
        inverse="_reflect_change_in_res_users_settings",
        groups="base.group_user",
    )
    voip_username = fields.Char(
        compute="_compute_voip_username",
        inverse="_reflect_change_in_res_users_settings",
        groups="base.group_user",
    )

    @property
    def SELF_READABLE_FIELDS(self):
        return super().SELF_READABLE_FIELDS + self._get_voip_user_configuration_fields()

    @property
    def SELF_WRITEABLE_FIELDS(self):
        return super().SELF_WRITEABLE_FIELDS + self._get_voip_user_configuration_fields()

    @api.depends("res_users_settings_id.external_device_number")
    def _compute_external_device_number(self):
        for user in self:
            user.external_device_number = user.res_users_settings_id.external_device_number

    @api.depends("res_users_settings_id.how_to_call_on_mobile")
    def _compute_how_to_call_on_mobile(self):
        for user in self:
            user.how_to_call_on_mobile = user.res_users_settings_id.how_to_call_on_mobile

    @api.depends("res_users_settings_id.should_auto_reject_incoming_calls")
    def _compute_should_auto_reject_incoming_calls(self):
        for user in self:
            user.should_auto_reject_incoming_calls = user.res_users_settings_id.should_auto_reject_incoming_calls

    @api.depends("res_users_settings_id.should_call_from_another_device")
    def _compute_should_call_from_another_device(self):
        for user in self:
            user.should_call_from_another_device = user.res_users_settings_id.should_call_from_another_device

    @api.depends("res_users_settings_id.voip_provider_id")
    def _compute_voip_provider_id(self):
        for user in self:
            user.voip_provider_id = user.res_users_settings_id.voip_provider_id

    @api.depends("res_users_settings_id.voip_secret")
    def _compute_voip_secret(self):
        for user in self:
            user.voip_secret = user.res_users_settings_id.voip_secret

    @api.depends("res_users_settings_id.voip_username")
    def _compute_voip_username(self):
        for user in self:
            user.voip_username = user.res_users_settings_id.voip_username

    @api.model
    def _get_voip_user_configuration_fields(self) -> list[str]:
        """
        List of the VoIP-related fields that are configurable by the user using the
        `res.users` form view. Useful to override SELF_READABLE/WRITABLE_FIELDS.
        """
        return [
            "external_device_number",
            "how_to_call_on_mobile",
            "should_auto_reject_incoming_calls",
            "should_call_from_another_device",
            "voip_secret",
            "voip_username",
            "voip_provider_id",
        ]

    @api.model
    def reset_last_seen_phone_call(self):
        domain = [("user_id", "=", self.env.user.id)]
        last_call = self.env["voip.call"].search(domain, order="id desc", limit=1)
        self.env.user.last_seen_phone_call = last_call.id

    def _init_store_data(self, store):
        super()._init_store_data(store)
        if not self.env.user._is_internal():
            return
        provider = self.env.user.voip_provider_id
        voip_config = {
            "mode": provider.mode or "demo",
            "missedCalls": self.env["voip.call"]._get_number_of_missed_calls(),
            "pbxAddress": provider.pbx_ip or "localhost",
            "webSocketUrl": provider.ws_server or "ws://localhost",
        }
        store.add({"voipConfig": voip_config})

    def _reflect_change_in_res_users_settings(self):
        """
        Updates the values of the VoIP User Configuration Fields in `res_users_settings_ids` to have the same values as
        their related fields in `res.users`. If there is no `res.users.settings` record for the user, then the record is
        created.

        This method is intended to be used as an inverse for VoIP Configuration Fields.
        """
        for user in self:
            settings = self.env["res.users.settings"]._find_or_create_for_user(user)
            configuration = {field: user[field] for field in self._get_voip_user_configuration_fields()}
            configuration["how_to_call_on_mobile"] = user.how_to_call_on_mobile or settings.how_to_call_on_mobile
            settings.update(configuration)
