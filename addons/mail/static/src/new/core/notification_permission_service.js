/** @odoo-module */

import { reactive } from "@odoo/owl";

import { browser } from "@web/core/browser/browser";
import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";

export const notificationPermissionService = {
    dependencies: ["notification"],

    async start(env, { notification }) {
        const permission = await browser.navigator?.permissions?.query({
            name: "notifications",
        });
        const state = reactive({
            /** @type {"prompt" | "granted" | "denied"} */
            permission: permission?.state ?? "denied",
            async requestPermission() {
                if (browser.Notification && state.permission === "prompt") {
                    const newPermission = await browser.Notification.requestPermission();
                    state.permission = newPermission === "default" ? "prompt" : newPermission;
                    if (state.permission === "denied") {
                        notification.add(
                            _t(
                                "Odoo will not have the permission to send native notifications on this device."
                            ),
                            {
                                type: "warning",
                                title: _t("Permission denied"),
                            }
                        );
                    }
                }
            },
        });
        if (permission) {
            permission.addEventListener("change", () => (state.permission = permission.state));
        }
        return state;
    },
};

registry.category("services").add("mail.notification.permission", notificationPermissionService);
