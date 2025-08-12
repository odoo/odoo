import { fields, getKwArgs, webModels } from "@web/../tests/web_test_helpers";
import { ensureArray } from "@web/core/utils/arrays";
import { patch } from "@web/core/utils/patch";

/**
 * @template T
 * @typedef {import("@web/../tests/web_test_helpers").KwArgs<T>} KwArgs
 */

export class ResUsersSettings extends webModels.ResUsersSettings {
    is_discuss_sidebar_category_channel_open = fields.Generic({ default: true });
    is_discuss_sidebar_category_chat_open = fields.Generic({ default: true });

    /**
     * @param {number} guest_id
     * @param {number} partner_id
     * @param {number} volume
     */
    set_volume_setting(ids, partner_id, volume, guest_id = false) {
        const kwargs = getKwArgs(arguments, "ids", "partner_id", "volume", "guest_id");
        ids = kwargs.ids;
        partner_id = kwargs.partner_id;
        volume = kwargs.volume;
        guest_id = kwargs.guest_id;

        /** @type {import("mock_models").BusBus} */
        const BusBus = this.env["bus.bus"];
        /** @type {import("mock_models").ResPartner} */
        const ResPartner = this.env["res.partner"];
        /** @type {import("mock_models").ResUsersSettingsVolumes} */
        const ResUsersSettingsVolumes = this.env["res.users.settings.volumes"];

        const id = ids[0]; // ensure_one
        let [volumeSettings] = ResUsersSettingsVolumes.search_read([
            ["user_setting_id", "=", id],
            partner_id ? ["partner_id", "=", partner_id] : ["guest_id", "=", guest_id],
        ]);
        if (!volumeSettings) {
            volumeSettings = ResUsersSettingsVolumes.create({
                partner_id,
                guest_id,
                volume,
            });
        } else {
            ResUsersSettingsVolumes.write(volumeSettings.id, { volume });
        }
        const [partner] = ResPartner.read(this.env.user.partner_id);
        BusBus._sendone(partner, "res.users.settings.volumes", {
            ...ResUsersSettingsVolumes.discuss_users_settings_volume_format(volumeSettings.id),
        });
        return volumeSettings;
    }

    set_custom_notifications(ids, custom_notifications) {
        const kwargs = getKwArgs(arguments, "ids", "custom_notifications");
        ids = kwargs.ids;
        delete kwargs.ids;
        custom_notifications = kwargs.custom_notifications;
        this.set_res_users_settings(ids, { channel_notifications: custom_notifications });
    }
}

patch(webModels.ResUsersSettings.prototype, {
    res_users_settings_format(id, fields_to_format) {
        const kwargs = getKwArgs(arguments, "id", "fields_to_format");
        id = kwargs.id;
        delete kwargs.id;
        fields_to_format = kwargs.fields_to_format;
        const res = super.res_users_settings_format(id, fields_to_format);

        /** @type {import("mock_models").ResUsersSettingsVolumes} */
        const ResUsersSettingsVolumes = this.env["res.users.settings.volumes"];

        const [settings] = this.browse(id);
        if (Reflect.ownKeys(res).includes("volume_settings_ids")) {
            const volumeSettings = ResUsersSettingsVolumes.discuss_users_settings_volume_format(
                settings.volume_settings_ids
            );
            res.volumes = [["ADD", volumeSettings]];
        }
        return res;
    },
    set_res_users_settings(idOrIds, new_settings) {
        const kwargs = getKwArgs(arguments, "idOrIds", "new_settings");
        idOrIds = kwargs.idOrIds;
        delete kwargs.idOrIds;
        new_settings = kwargs.new_settings || {};
        const changedSettings = super.set_res_users_settings(idOrIds, new_settings);

        /** @type {import("mock_models").BusBus} */
        const BusBus = this.env["bus.bus"];
        /** @type {import("mock_models").ResPartner} */
        const ResPartner = this.env["res.partner"];
        /** @type {import("mock_models").ResUsers} */
        const ResUsers = this.env["res.users"];

        const [id] = ensureArray(idOrIds);
        const [oldSettings] = this.browse(id);
        const [relatedUser] = ResUsers.search_read([["id", "=", oldSettings.user_id]]);
        const [relatedPartner] = ResPartner.search_read([["id", "=", relatedUser.partner_id[0]]]);
        BusBus._sendone(relatedPartner, "res.users.settings", {
            ...changedSettings,
            id,
        });
        return changedSettings;
    },
});
