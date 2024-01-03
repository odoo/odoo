/** @odoo-module */

import { fields, models } from "@web/../tests/web_test_helpers";
import { ensureArray } from "@web/core/utils/arrays";

/**
 * @template T
 * @typedef {import("@web/../tests/web_test_helpers").KwArgs<T>} KwArgs
 */

const ORM_AUTOMATIC_FIELDS = new Set([
    "create_date",
    "create_uid",
    "display_name",
    "name",
    "write_date",
    "write_uid",
]);

export class ResUsersSettings extends models.ServerModel {
    _name = "res.users.settings";

    is_discuss_sidebar_category_channel_open = fields.Generic({ default: true });
    is_discuss_sidebar_category_chat_open = fields.Generic({ default: true });

    /**
     * Simulates `_find_or_create_for_user` on `res.users.settings`.
     * Note that this mocked method is public so that it can be accessed by RPCs.
     *
     * @param {number} userId
     * @param {KwArgs} [kwargs]
     */
    find_or_create_for_user(userId, kwargs = {}) {
        const settings = this._filter([["user_id", "=", userId]])[0];
        if (settings) {
            return settings;
        }
        const settingsId = this.create({ user_id: userId });
        return this._filter([["id", "=", settingsId]])[0];
    }

    /**
     * Simulates `res_users_settings_format` on `res.users.settings`.
     *
     * @param {number} id
     * @param {string[]} [fieldsToFormat]
     * @param {KwArgs<{ fields_to_format }>} [kwargs]
     */
    res_users_settings_format(id, fieldsToFormat, kwargs = {}) {
        fieldsToFormat = kwargs.fields_to_format || fieldsToFormat;
        const [settings] = this._filter([["id", "=", id]]);
        const filterPredicate = fieldsToFormat
            ? ([fieldName]) => fieldsToFormat.includes(fieldName)
            : ([fieldName]) => !ORM_AUTOMATIC_FIELDS.has(fieldName);
        const res = Object.fromEntries(Object.entries(settings).filter(filterPredicate));
        if (Reflect.ownKeys(res).includes("user_id")) {
            res.user_id = { id: settings.user_id };
        }
        if (Reflect.ownKeys(res).includes("volume_settings_ids")) {
            const volumeSettings = this.env[
                "res.users.settings.volumes"
            ].discuss_users_settings_volume_format(settings.volume_settings_ids);
            res.volumes = [["ADD", volumeSettings]];
        }
        return res;
    }

    /**
     * Simulates `set_res_users_settings` on `res.users.settings`.
     *
     * @param {number | Iterable<number>} idOrIds
     * @param {Object} newSettings
     * @param {KwArgs<{ new_settings }>} [kwargs]
     */
    set_res_users_settings(idOrIds, newSettings, kwargs = {}) {
        newSettings = kwargs.new_settings || newSettings || {};
        const [id] = ensureArray(idOrIds);
        const oldSettings = this._filter([["id", "=", id]])[0];
        const changedSettings = {};
        for (const setting in newSettings) {
            if (setting in oldSettings && newSettings[setting] !== oldSettings[setting]) {
                changedSettings[setting] = newSettings[setting];
            }
        }
        this.write(id, changedSettings);
        const [relatedUser] = this.env["res.users"].search_read([["id", "=", oldSettings.user_id]]);
        const [relatedPartner] = this.env["res.partner"].search_read([
            ["id", "=", relatedUser.partner_id[0]],
        ]);
        this.env["bus.bus"]._sendone(relatedPartner, "res.users.settings", {
            ...changedSettings,
            id,
        });
    }
}
