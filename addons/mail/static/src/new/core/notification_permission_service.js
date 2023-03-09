/** @odoo-module */

import { reactive } from "@odoo/owl";

import { browser } from "@web/core/browser/browser";
import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";

export const notificationPermissionService = {
    dependencies: ["notification"],

    _normalizePermission(permission) {
        switch (permission) {
            case "default":
                return "prompt";
            case undefined:
                return "denied";
            default:
                return permission;
        }
    },

    async start(env, { notification }) {
        let permission;
        try {
            permission = await browser.navigator?.permissions?.query({
                name: "notifications",
            });
        } catch {
            // noop
        }
        const state = reactive({
            /** @type {"prompt" | "granted" | "denied"} */
            permission: this._normalizePermission(
                permission?.state ?? browser.Notification?.permission
            ),
            requestPermission: async () => {
                if (browser.Notification && state.permission === "prompt") {
                    state.permission = this._normalizePermission(
                        await browser.Notification.requestPermission()
                    );
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
