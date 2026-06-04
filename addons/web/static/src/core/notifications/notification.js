import { Component, useEffect, props, signal } from "@odoo/owl";
import { NotificationSchema } from "./notification_plugin";
import { useTimer } from "@web/core/utils/timing";

const AUTOCLOSE_DELAY = 4000;

export class Notification extends Component {
    static template = "web.NotificationWowl";
    // TODO-JUCOP: Why is the default part not applied ?
    notification = props.static("notification", NotificationSchema, {
        buttons: [],
        className: "",
        type: "warning",
        autocloseDelay: AUTOCLOSE_DELAY,
    });

    autocloseProgress = signal(null);

    setup() {
        if (!this.notification.sticky && (this.notification.autocloseDelay ?? AUTOCLOSE_DELAY) > 0) {
            this.timer = useTimer(this.notification.autocloseDelay ?? AUTOCLOSE_DELAY);

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
