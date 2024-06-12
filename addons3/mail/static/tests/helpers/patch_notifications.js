/* @odoo-module */

import { browser } from "@web/core/browser/browser";
import { patchWithCleanup } from "@web/../tests/helpers/utils";

/**
 * Patch both the `Notification` and the `Permissions` API which are codependent
 * based on the given value. Note that when `requestPermissionResult` is passed,
 * the `change` event of the `Permissions` API will also be triggered.
 *
 * @param {"default" | "denied" | "granted"} permission
 * @param {"default" | "denied" | "granted"} requestPermissionResult
 */
export function patchBrowserNotification(permission = "default", requestPermissionResult) {
    if (!browser.Notification || !browser.navigator.permissions) {
        return;
    }
    const notificationQueries = [];
    patchWithCleanup(browser.navigator.permissions, {
        async query({ name }) {
            const result = await super.query(...arguments);
            if (name === "notifications") {
                Object.defineProperty(result, "state", {
                    get: () => (permission === "default" ? "prompt" : permission),
                });
                notificationQueries.push(result);
            }
            return result;
        },
    });
    patchWithCleanup(browser.Notification, {
        permission,
        isPatched: true,
        requestPermission() {
            if (!requestPermissionResult) {
                return super.requestPermission(...arguments);
            }
            this.permission = requestPermissionResult;
            for (const query of notificationQueries) {
                query.permission = requestPermissionResult;
                query.dispatchEvent(new Event("change"));
            }
            return requestPermissionResult;
        },
    });
}
