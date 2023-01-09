/** @odoo-module **/

import { patch } from "@web/core/utils/patch";
import { MockServer } from "@web/../tests/helpers/mock_server";

patch(MockServer.prototype, "mail/models/res_users_settings", {
    async _performRPC(route, args) {
        if (args.model === "res.users.settings" && args.method === "_find_or_create_for_user") {
            const user_id = args.args[0][0];
            return this._mockResUsersSettings_FindOrCreateForUser(user_id);
        }
        if (args.model === "res.users.settings" && args.method === "set_res_users_settings") {
            const id = args.args[0][0];
            const newSettings = args.kwargs.new_settings;
            return this._mockResUsersSettingsSetResUsersSettings(id, newSettings);
        }
        return this._super(route, args);
    },
    /**
     * Simulates `_find_or_create_for_user` on `res.users.settings`.
     *
     * @param {Object} user
     * @returns {Object}
     */
    _mockResUsersSettings_FindOrCreateForUser(user_id) {
        let settings = this.getRecords("res.users.settings", [["user_id", "=", user_id]])[0];
        if (!settings) {
            const settingsId = this.pyEnv["res.users.settings"].create({ user_id: user_id });
            settings = this.getRecords("res.users.settings", [["id", "=", settingsId]])[0];
        }
        return settings;
    },

    /**
     * Simulates `res_users_settings_format` on `res.users.settings`.
     *
     * @param {integer} id
     * @param {string[]} [fieldsToFormat]
     * @returns {Object}
     */
    _mockResUsersSettings_ResUsersSettingsFormat(id, fieldsToFormat) {
        const [settings] = this.getRecords("res.users.settings", [["id", "=", id]]);
        const ormAutomaticFields = new Set([
            "create_date",
            "create_uid",
            "display_name",
            "name",
            "write_date",
            "write_uid",
        ]);
        const filterPredicate = fieldsToFormat
            ? ([fieldName]) => fieldsToFormat.includes(fieldName)
            : ([fieldName]) => !ormAutomaticFields.has(fieldName);
        const res = Object.fromEntries(Object.entries(settings).filter(filterPredicate));
        if (Object.prototype.hasOwnProperty.call(res, "user_id")) {
            res.user_id = { id: settings.user_id };
        }
        if (Object.prototype.hasOwnProperty.call(res, "volume_settings_ids")) {
            const volumeSettings = this._mockResUsersSettingsVolumes_DiscussUsersSettingsVolumeFormat(
                settings.volume_settings_ids
            );
            res.volume_settings_ids = [["insert", volumeSettings]];
        }
        return res;
    },

    /**
     * Simulates `set_res_users_settings` on `res.users.settings`.
     *
     * @param {integer} id
     * @param {Object} newSettings
     */
    _mockResUsersSettingsSetResUsersSettings(id, newSettings) {
        const oldSettings = this.getRecords("res.users.settings", [["id", "=", id]])[0];
        const changedSettings = {};
        for (const setting in newSettings) {
            if (setting in oldSettings && newSettings[setting] !== oldSettings[setting]) {
                changedSettings[setting] = newSettings[setting];
            }
        }
        this.pyEnv["res.users.settings"].write([id], changedSettings);
        const [relatedUser] = this.pyEnv["res.users"].searchRead([
            ["id", "=", oldSettings.user_id],
        ]);
        const [relatedPartner] = this.pyEnv["res.partner"].searchRead([
            ["id", "=", relatedUser.partner_id],
        ]);
        this.pyEnv["bus.bus"]._sendone(relatedPartner, "mail.record/insert", {
            "res.users.settings": { ...changedSettings, id },
        });
    },
});
