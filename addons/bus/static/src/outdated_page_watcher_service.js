import { EventBus } from "@odoo/owl";
import { rpc } from "@web/core/network/rpc";
import { registry } from "@web/core/registry";

export class OutdatedPageWatcherService {
    constructor(env, services) {
        this.setup(env, services);
    }

    /**
     * @param {import("@web/env").OdooEnv}
     * @param {Partial<import("services").Services>} services
     */
    setup(env, { bus_service, multi_tab, notification }) {
        this.bus = new EventBus();
        this.notification = notification;
        this.multi_tab = multi_tab;
        this.lastNotificationId = null;
        this.closeNotificationFn;
        let wasBusAlreadyConnected;
        bus_service.addEventListener(
            "worker_state_updated",
            ({ detail: state }) => {
                wasBusAlreadyConnected = state !== "IDLE";
            },
            { once: true }
        );
        bus_service.addEventListener(
            "disconnect",
            () => (this.lastNotificationId = bus_service.lastNotificationId)
        );
        bus_service.addEventListener("connect", async () => {
            if (wasBusAlreadyConnected) {
                this.checkHasMissedNotifications();
            }
            wasBusAlreadyConnected = true;
        });
        bus_service.addEventListener("reconnect", () => this.checkHasMissedNotifications());
        multi_tab.bus.addEventListener("shared_value_updated", ({ detail: { key } }) => {
            if (key === "bus.has_missed_notifications") {
                this.bus.trigger("outdated_page");
            }
        });
    }

    async checkHasMissedNotifications() {
        if (!this.multi_tab.isOnMainTab()) {
            return;
        }
        const hasMissedNotifications = await rpc(
            "/bus/has_missed_notifications",
            { last_notification_id: this.lastNotificationId },
            { silent: true }
        );
        if (hasMissedNotifications) {
            this.bus.trigger("outdated_page");
            this.multi_tab.setSharedValue("bus.has_missed_notifications", Date.now());
        }
    }

    /** Register a callback to be executed when notifications are missed. */
    subscribe(fn) {
        this.bus.addEventListener("outdated_page", fn);
    }
}

export const outdatedPageWatcherService = {
    dependencies: ["bus_service", "multi_tab", "notification"],
    start(env, services) {
        return new OutdatedPageWatcherService(env, services);
    },
};

registry.category("services").add("bus.outdated_page_watcher", outdatedPageWatcherService);
