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
                value: this.store.settings.channel_push,
            },
            {
                label: "chat_push",
                name: _t("Direct Messages"),
                value: this.store.settings.chat_push,
            },
            {
                label: "inbox_push",
                name: _t("Inbox"),
                value: this.store.settings.inbox_push,
            },
        ];
    }

    get canSendPushNotification() {
        return window.Notification?.permission === "granted" || this.isAndroidApp || this.isIosApp;
    }
}
