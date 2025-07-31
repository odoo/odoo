import { ServerModel } from "../mock_model";
import { getKwArgs } from "../mock_server_utils";
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

export class ResUsersSettings extends ServerModel {
    // TODO: merge this class with mail models
    _name = "res.users.settings";

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

        const [settings] = this.browse(id);
        const filterPredicate = fields_to_format
            ? ([fieldName]) => fields_to_format.includes(fieldName)
            : ([fieldName]) => !ORM_AUTOMATIC_FIELDS.has(fieldName);
        const res = Object.fromEntries(Object.entries(settings).filter(filterPredicate));
        if (Reflect.ownKeys(res).includes("user_id")) {
            res.user_id = { id: settings.user_id };
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

        const [id] = ensureArray(idOrIds);
        const [oldSettings] = this.browse(id);
        const changedSettings = {};
        for (const setting in new_settings) {
            if (setting in oldSettings && new_settings[setting] !== oldSettings[setting]) {
                changedSettings[setting] = new_settings[setting];
            }
        }
        this.write(id, changedSettings);
        return changedSettings;
    }
}
