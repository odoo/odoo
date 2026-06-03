import { Component, onMounted, signal, applyDefaults, useProps } from "@odoo/owl";
import { NotificationSchema } from "./notification_plugin";

export class Notification extends Component {
    static template = "web.NotificationWowl";
    props = applyDefaults(useProps(NotificationSchema.toShape()), NotificationSchema);

    autocloseProgress = signal.ref();

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
        this.props.close();
    }

    startNotificationTimer() {
        if (this.props.sticky) {
            return;
        }
        this.startedTimestamp = luxon.DateTime.now().ts;

        const cb = () => {
            if (this.startedTimestamp) {
                const currentProgress =
                    (luxon.DateTime.now().ts - this.startedTimestamp) / this.props.autocloseDelay;
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
