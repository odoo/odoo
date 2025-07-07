import { browser } from "@web/core/browser/browser";
import { _t } from "@web/core/l10n/translation";
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
    setup(env, { bus_service, multi_tab, legacy_multi_tab, notification }) {
        this.notification = notification;
        this.multi_tab = multi_tab;
        this.legacy_multi_tab = legacy_multi_tab;
        this.lastNotificationId = legacy_multi_tab.getSharedValue("last_notification_id");
        this.closeNotificationFn;
        let wasBusAlreadyConnected;
        bus_service.addEventListener(
            "BUS:WORKER_STATE_UPDATED",
            ({ detail: state }) => {
                wasBusAlreadyConnected = state !== "IDLE";
            },
            { once: true }
        );
        bus_service.addEventListener(
            "BUS:DISCONNECT",
            () =>
                (this.lastNotificationId = legacy_multi_tab.getSharedValue("last_notification_id"))
        );
        bus_service.addEventListener("BUS:CONNECT", async () => {
            if (wasBusAlreadyConnected) {
                this.checkHasMissedNotifications();
            }
            wasBusAlreadyConnected = true;
        });
        bus_service.addEventListener("BUS:RECONNECT", () => this.checkHasMissedNotifications());
        legacy_multi_tab.bus.addEventListener("shared_value_updated", ({ detail: { key } }) => {
            if (key === "bus.has_missed_notifications") {
                this.showOutdatedPageNotification();
            }
        });
    }

    async checkHasMissedNotifications() {
        if (!this.lastNotificationId || !(await this.multi_tab.isOnMainTab())) {
            return;
        }
        const hasMissedNotifications = await rpc(
            "/bus/has_missed_notifications",
            { last_notification_id: this.lastNotificationId },
            { silent: true }
        );
        if (hasMissedNotifications) {
            this.showOutdatedPageNotification();
            this.legacy_multi_tab.setSharedValue("bus.has_missed_notifications", Date.now());
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
    dependencies: ["bus_service", "multi_tab", "legacy_multi_tab", "notification"],
    start(env, services) {
        return new OutdatedPageWatcherService(env, services);
    },
};

registry.category("services").add("bus.outdated_page_watcher", outdatedPageWatcherService);
