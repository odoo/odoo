import { BusPlugin } from "@bus/services/bus_plugin";
import { onWillDestroy, Plugin, usePlugin } from "@odoo/owl";
import { _t } from "@web/core/l10n/translation";
import { NotificationPlugin } from "@web/core/notifications/notification_plugin";
import { services } from "@web/core/services";

export class IapNotificationPlugin extends Plugin {
    bus = usePlugin(BusPlugin);
    notification = usePlugin(NotificationPlugin);

    setup() {
        const unsubscribe = this.bus.subscribe("iap_notification", (params) => {
            if (params.type == "no_credit") {
                this._displayCreditErrorNotification(params);
            } else {
                this._displayNotification(params);
            }
        });
        this.bus.start();

        onWillDestroy(unsubscribe);
    }

    /** @private */
    _displayNotification(params) {
        this.notification.add(params.message, {
            title: params.title,
            type: params.type,
        });
    }

    /** @private */
    _displayCreditErrorNotification(params) {
        this.notification.add(params.title, {
            type: "danger",
            buttons: [
                {
                    name: _t("Buy"),
                    onClick: () => {
                        window.open(params.get_credits_url, "_blank");
                    },
                },
            ],
        });
    }
}

services.add(IapNotificationPlugin);
