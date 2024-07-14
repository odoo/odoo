/* @odoo-module */

import { UserSettings } from "@mail/core/common/user_settings_service";

import { patch } from "@web/core/utils/patch";

const VOIP_CONFIG_KEYS = [
    "external_device_number",
    "how_to_call_on_mobile",
    "should_auto_reject_incoming_calls",
    "should_call_from_another_device",
    "voip_secret",
    "voip_username",
];

patch(UserSettings.prototype, {
    /** @override */
    updateFromCommands(settings) {
        super.updateFromCommands(settings);
        for (const key of VOIP_CONFIG_KEYS) {
            if (key in settings) {
                this[key] = settings[key];
            }
        }
    },
});
