import { Record, fields } from "@mail/model/export";

import { browser } from "@web/core/browser/browser";

export class ResUsersSettings extends Record {
    static _name = "res.users.settings";

    id;
    /**
     * Raw server value; the server sends `false` for default (which is Mentions).
     *
     * @type {"all"|"no_notif"|false}
     */
    channel_notifications;
    /** @type {"mentions"|"all"|"no_notif"} */
    get channelNotifications() {
        return this.channel_notifications === false ? "mentions" : this.channel_notifications;
    }
    /** @type {boolean} */
    channel_push;
    /** @type {boolean} */
    chat_push;
    /** @type {boolean} */
    inbox_push;
    volume_settings_ids = fields.Many("res.users.settings.volumes", {
        inverse: "user_setting_id",
    });
    volumeSettingsTimeouts = new Map();

    /**
     * @param {Object} param0
     * @param {number} [param0.partnerId]
     * @param {number} [param0.guestId]
     * @param {number} param0.volume
     */
    async saveVolumeSetting({ partnerId, guestId, volume }) {
        if (!this.store.self_user) {
            return;
        }
        const key = `${partnerId}_${guestId}`;
        if (this.volumeSettingsTimeouts.get(key)) {
            browser.clearTimeout(this.volumeSettingsTimeouts.get(key));
        }
        this.volumeSettingsTimeouts.set(
            key,
            browser.setTimeout(
                this._onSaveVolumeSettingTimeout.bind(this, { key, partnerId, guestId, volume }),
                5000
            )
        );
    }

    /**
     * @param {Object} param0
     * @param {String} param0.key
     * @param {number} [param0.partnerId]
     * @param {number} param0.volume
     */
    async _onSaveVolumeSettingTimeout({ key, partnerId, guestId, volume }) {
        this.volumeSettingsTimeouts.delete(key);
        await this.store.env.services.orm.call(
            "res.users.settings",
            "set_volume_setting",
            [[this.id], partnerId, volume],
            { guest_id: guestId }
        );
    }
}

ResUsersSettings.register();
