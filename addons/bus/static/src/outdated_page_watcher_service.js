import { browser } from "@web/core/browser/browser";
import { _t } from "@web/core/l10n/translation";
import { rpc } from "@web/core/network/rpc";
import { registry } from "@web/core/registry";

const { DateTime } = luxon;
export class OutdatedPageWatcherService {
    constructor(env, services) {
        this.setup(env, services);
    }

    /**
     * @param {import("@web/env").OdooEnv}
     * @param {Partial<import("services").Services>} services
     */
    setup(env, { bus_service, multi_tab, notification }) {
        this.notification = notification;
        this.multi_tab = multi_tab;
        this.lastNotificationId = multi_tab.getSharedValue("last_notification_id");
        /** @deprecated */
        this.lastDisconnectDt = null;
        this.closeNotificationFn;
        let wasBusAlreadyConnected;
        bus_service.addEventListener(
            "worker_state_updated",
            ({ detail: state }) => {
                wasBusAlreadyConnected = state !== "IDLE";
            },
            { once: true }
        );
        bus_service.addEventListener("disconnect", () => {
            this.lastNotificationId = multi_tab.getSharedValue("last_notification_id");
            this.lastDisconnectDt = DateTime.now();
        });
        bus_service.addEventListener("connect", async () => {
            if (wasBusAlreadyConnected) {
                this.checkHasMissedNotifications();
            }
            wasBusAlreadyConnected = true;
        });
        bus_service.addEventListener("reconnect", () => this.checkHasMissedNotifications());
        multi_tab.bus.addEventListener("shared_value_updated", ({ detail: { key } }) => {
            if (key === "bus.has_missed_notifications") {
                this.showOutdatedPageNotification();
            }
        });
    }

    async checkHasMissedNotifications() {
        if (!this.multi_tab.isOnMainTab() || !this.lastNotificationId) {
            return;
        }
        const hasMissedNotifications = await rpc(
            "/bus/has_missed_notifications",
            { last_notification_id: this.lastNotificationId },
            { silent: true }
        );
        if (hasMissedNotifications) {
            this.showOutdatedPageNotification();
            this.multi_tab.setSharedValue("bus.has_missed_notifications", Date.now());
        }
    }

    showOutdatedPageNotification() {
        this.closeNotificationFn?.();
        this.closeNotificationFn = this.notification.add(
            _t("Save your work and refresh to get the latest updates and avoid potential issues."),
            {
                title: _t("The page is out of date"),
                type: "warning",
                sticky: true,
                buttons: [
                    {
                        name: _t("Refresh"),
                        primary: true,
                        onClick: () => browser.location.reload(),
                    },
                ],
            }
        );
    }
}

export const outdatedPageWatcherService = {
    dependencies: ["bus_service", "multi_tab", "notification"],
    start(env, services) {
        return new OutdatedPageWatcherService(env, services);
    },
};

registry.category("services").add("bus.outdated_page_watcher", outdatedPageWatcherService);
