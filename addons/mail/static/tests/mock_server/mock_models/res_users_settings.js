import { fields, getKwArgs, models } from "@web/../tests/web_test_helpers";
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

    /** @param {number|number[]} userIdOrIds */
    _find_or_create_for_user(userIdOrIds) {
        const [userId] = ensureArray(userIdOrIds);
        const settings = this._filter([["user_id", "=", userId]])[0];
        if (settings) {
            return settings;
        }
        const settingsId = this.create({ user_id: userId });
        return this.browse(settingsId)[0];
    }

    /**
     * @param {number} id
     * @param {string[]} [fields_to_format]
     */
    res_users_settings_format(id, fields_to_format) {
        const kwargs = getKwArgs(arguments, "id", "fields_to_format");
        id = kwargs.id;
        delete kwargs.id;
        fields_to_format = kwargs.fields_to_format;

        /** @type {import("mock_models").ResUsersSettingsVolumes} */
        const ResUsersSettingsVolumes = this.env["res.users.settings.volumes"];

        const [settings] = this.browse(id);
        const filterPredicate = fields_to_format
            ? ([fieldName]) => fields_to_format.includes(fieldName)
            : ([fieldName]) => !ORM_AUTOMATIC_FIELDS.has(fieldName);
        const res = Object.fromEntries(Object.entries(settings).filter(filterPredicate));
        if (Reflect.ownKeys(res).includes("user_id")) {
            res.user_id = { id: settings.user_id };
        }
        if (Reflect.ownKeys(res).includes("volume_settings_ids")) {
            const volumeSettings = ResUsersSettingsVolumes.discuss_users_settings_volume_format(
                settings.volume_settings_ids
            );
            res.volumes = [["ADD", volumeSettings]];
        }
        return res;
    }

    /**
     * @param {number | Iterable<number>} idOrIds
     * @param {Object} newSettings
     * @param {KwArgs<{ new_settings }>} [kwargs]
     */
    set_res_users_settings(idOrIds, new_settings) {
        const kwargs = getKwArgs(arguments, "idOrIds", "new_settings");
        idOrIds = kwargs.idOrIds;
        delete kwargs.idOrIds;
        new_settings = kwargs.new_settings || {};

        /** @type {import("mock_models").BusBus} */
        const BusBus = this.env["bus.bus"];
        /** @type {import("mock_models").ResPartner} */
        const ResPartner = this.env["res.partner"];
        /** @type {import("mock_models").ResUsers} */
        const ResUsers = this.env["res.users"];

        const [id] = ensureArray(idOrIds);
        const [oldSettings] = this.browse(id);
        const changedSettings = {};
        for (const setting in new_settings) {
            if (setting in oldSettings && new_settings[setting] !== oldSettings[setting]) {
                changedSettings[setting] = new_settings[setting];
            }
        }
        this.write(id, changedSettings);
        const [relatedUser] = ResUsers.search_read([["id", "=", oldSettings.user_id]]);
        const [relatedPartner] = ResPartner.search_read([["id", "=", relatedUser.partner_id[0]]]);
        BusBus._sendone(relatedPartner, "res.users.settings", {
            ...changedSettings,
            id,
        });
    }
}
