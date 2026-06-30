import { _t } from "@web/core/l10n/translation";
import { browser } from "@web/core/browser/browser";
import { registry } from "@web/core/registry";
import { session } from "@web/session";

export const assetsWatchdogService = {
    dependencies: ["bus_service", "notification"],

    start(env, { bus_service, notification }) {
        let isNotificationDisplayed = false;
        let bundleNotifTimerID = null;

        bus_service.subscribe("bundle_changed", ({ server_version }) => {
            if (server_version !== session.server_version) {
                displayBundleChangedNotification();
            }
        });
        bus_service.start();

        /**
         * Displays one notification on user's screen when assets have changed
         */
        function displayBundleChangedNotification() {
            if (!isNotificationDisplayed) {
                // Wrap the notification inside a delay.
                // The server may be overwhelmed with recomputing assets
                // We wait until things settle down
                browser.clearTimeout(bundleNotifTimerID);
                bundleNotifTimerID = browser.setTimeout(() => {
                    notification.add(_t("The page appears to be out of date."), {
                        title: _t("Refresh"),
                        type: "warning",
                        sticky: true,
                        buttons: [
                            {
                                name: _t("Refresh"),
                                primary: true,
                                onClick: () => {
                                    browser.location.reload();
                                },
                            },
                        ],
                        onClose: () => {
                            isNotificationDisplayed = false;
                        },
                    });
                    isNotificationDisplayed = true;
                }, getBundleNotificationDelay());
            }
        }

        /**
         * Computes a random delay to avoid hammering the server
         * when bundles change with all the users reloading
         * at the same time
         *
         * @return {number} delay in milliseconds
         */
        function getBundleNotificationDelay() {
            return 10000 + Math.floor(Math.random() * 50) * 1000;
        }
    },
};

registry.category("services").add("assetsWatchdog", assetsWatchdogService);
