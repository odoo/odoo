import { Component, useState } from "@odoo/owl";
import { isAndroidApp, isIosApp } from "@web/core/browser/feature_detection";
import { useService } from "@web/core/utils/hooks";

export class DiscussNotificationSettings extends Component {
    static props = {};
    static template = "mail.DiscussNotificationSettings";

    setup() {
        this.store = useService("mail.store");
        this.state = useState({
            selectedDuration: false,
        });
        this.isIosApp = isIosApp();
        this.isAndroidApp = isAndroidApp();
    }

    onChangeMessageSound() {
        this.store.settings.messageSound = !this.store.settings.messageSound;
    }

    get canSendPushNotification() {
        return Boolean(window.Notification && window.Notification.permission === "granted");
    }
}
