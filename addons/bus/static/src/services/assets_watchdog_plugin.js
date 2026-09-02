import { _t } from "@web/core/l10n/translation";
import { location, browser } from "@web/core/browser/browser";
import { registry } from "@web/core/registry";
import { session } from "@web/session";
import { Plugin, usePlugin } from "@odoo/owl";
import { BusPlugin } from "@bus/services/bus_plugin";
import { NotificationPlugin } from "@web/core/notifications/notification_plugin";
import { services } from "@web/core/services";

export class AssetsWatchdogPlugin extends Plugin {
    /** @private */
    busService = usePlugin(BusPlugin);
    /** @private */
    notification = usePlugin(NotificationPlugin);

    /** @private */
    isNotificationDisplayed = false;
    /** @private */
    bundleNotifTimerID = null;

    setup() {
        this.busService.subscribe("bundle_changed", ({ server_version }) => {
            if (server_version !== session.server_version) {
                this.displayBundleChangedNotification();
            }
        });
        this.busService.start();
    }

    /**
     * @private
     * Displays one notification on user's screen when assets have changed
     */
    displayBundleChangedNotification() {
        if (!this.isNotificationDisplayed) {
            // Wrap the notification inside a delay.
            // The server may be overwhelmed with recomputing assets
            // We wait until things settle down
            browser.clearTimeout(this.bundleNotifTimerID);
            this.bundleNotifTimerID = browser.setTimeout(() => {
                this.notification.add(_t("The page appears to be out of date."), {
                    title: _t("Refresh"),
                    type: "warning",
                    sticky: true,
                    buttons: [
                        {
                            name: _t("Refresh"),
                            primary: true,
                            onClick: () => {
                                location.reload();
                            },
                        },
                    ],
                    onClose: () => {
                        this.isNotificationDisplayed = false;
                    },
                });
                this.isNotificationDisplayed = true;
            }, this.getBundleNotificationDelay());
        }
    }

    /**
     * @private
     * Computes a random delay to avoid hammering the server
     * when bundles change with all the users reloading
     * at the same time
     *
     * @return {number} delay in milliseconds
     */
    getBundleNotificationDelay() {
        return 10000 + Math.floor(Math.random() * 50) * 1000;
    }
}

services.add(AssetsWatchdogPlugin);

/**
 * -----------------------------------------------------------------------------
 * @todo owl3 migration
 * temporary - to remove when all use of the assetsWatchdog service are removed
 * -----------------------------------------------------------------------------
 */
registry.category("services").add("assetsWatchdog", {
    start() {
        return usePlugin(AssetsWatchdogPlugin);
    },
});
