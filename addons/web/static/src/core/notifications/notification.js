import { Component, useEffect, props, signal, applyDefaults } from "@odoo/owl";
import { NotificationSchema } from "./notification_plugin";
import { useTimer } from "@web/core/utils/timing";

export class Notification extends Component {
    static template = "web.NotificationWowl";
    notification = applyDefaults(props.static("notification", NotificationSchema), NotificationSchema);

    autocloseProgress = signal(null);

    setup() {
        if (!this.notification.sticky && this.notification.autocloseDelay > 0) {
            this.timer = useTimer(this.notification.autocloseDelay);

            useEffect(() => {
                if (this.timer.progress() >= 1) {
                    this.close();
                } else if (this.autocloseProgress()) {
                    this.autocloseProgress().style.width = `${(1 - this.timer.progress()) * 100}%`;
                }
            });
        }
    }

    freeze() {
        this.timer?.stop();
        if (this.autocloseProgress()) {
            this.autocloseProgress().style.width = 0;
        }
    }

    refresh() {
        this.timer?.reset();
    }

    close() {
        this.notification.close();
    }
}
