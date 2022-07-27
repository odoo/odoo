/** @odoo-module **/

import { browser } from "@web/core/browser/browser";
import { registry } from "@web/core/registry";
import { session } from "@web/session";

export const assetsWatchdogService = {
    dependencies: ["notification"],

    start(env, { notification }) {
        let isNotificationDisplayed = false;
        let bundleNotifTimerID = null;

        env.bus.on("WEB_CLIENT_READY", null, async () => {
            const legacyEnv = owl.Component.env;
            legacyEnv.services.bus_service.onNotification(this, onNotification);
            legacyEnv.services.bus_service.startPolling();
        });

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
                    notification.add(
                        env._t("The page appears to be out of date."),
                        {
                            title: env._t("Refresh"),
                            type: "warning",
                            sticky: true,
                            buttons: [
                                {
                                    name: env._t("Refresh"),
                                    primary: true,
                                    onClick: () => {
                                        browser.location.reload();
                                    },
                                },
                            ],
                            onClose: () => {
                                isNotificationDisplayed = false;
                            },
                        }
                    );
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

        /**
         * Reacts to bus's notification
         *
         * @param {Array} notifications: list of received notifications
         */
        function onNotification(notifications) {
            for (const { payload, type } of notifications) {
                if (type === 'bundle_changed') {
                    if (payload.server_version !== session.server_version) {
                        displayBundleChangedNotification();
                        break;
                    }
                }
            }
        }
    },
};

registry.category("services").add("assetsWatchdog", assetsWatchdogService);
