import { Component, onMounted, props, signal } from "@odoo/owl";
import { NotificationSchema } from "./notification_plugin";

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
        onMounted(() => this.startNotificationTimer());
    }

    freeze() {
        this.startedTimestamp = false;
        if (this.autocloseProgress()) {
            this.autocloseProgress().style.width = 0;
        }
    }

    refresh() {
        this.startNotificationTimer();
    }

    close() {
        this.notification.close();
    }

    startNotificationTimer() {
        if (this.notification.sticky) {
            return;
        }
        this.startedTimestamp = luxon.DateTime.now().ts;

        const cb = () => {
            if (this.startedTimestamp) {
                const currentProgress =
                    (luxon.DateTime.now().ts - this.startedTimestamp) / (this.notification.autocloseDelay ?? AUTOCLOSE_DELAY);
                if (currentProgress > 1) {
                    this.close();
                    return;
                }
                if (this.autocloseProgress()) {
                    this.autocloseProgress().style.width = `${(1 - currentProgress) * 100}%`;
                }
                requestAnimationFrame(cb);
            }
        };
        cb();
    }
}
