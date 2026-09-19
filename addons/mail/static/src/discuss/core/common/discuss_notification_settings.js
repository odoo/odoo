import { Component } from "@odoo/owl";
import { _t } from "@web/core/l10n/translation";
import { isAndroidApp, isIosApp } from "@web/core/browser/feature_detection";
import { useService } from "@web/core/utils/hooks";

export class DiscussNotificationSettings extends Component {
    static template = "mail.DiscussNotificationSettings";

    setup() {
        this.store = useService("mail.store");
        this.isAndroidApp = isAndroidApp();
        this.isIosApp = isIosApp();
    }

    onChangeMessageSound() {
        this.store.settings.messageSound = !this.store.settings.messageSound;
    }

    get PUSHNOTIFS() {
        return [
            {
                label: "channel_push",
                name: _t("Channels"),
                value: this.store.self_user.res_users_settings_id.channel_push,
            },
            {
                label: "chat_push",
                name: _t("Direct Messages"),
                value: this.store.self_user.res_users_settings_id.chat_push,
            },
            {
                label: "inbox_push",
                name: _t("Inbox"),
                value: this.store.self_user.res_users_settings_id.inbox_push,
            },
        ];
    }

    get canSendPushNotification() {
        return window.Notification?.permission === "granted" || this.isAndroidApp || this.isIosApp;
    }
}
