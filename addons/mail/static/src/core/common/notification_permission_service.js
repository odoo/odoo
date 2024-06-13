import { reactive } from "@odoo/owl";

import { browser } from "@web/core/browser/browser";
import { isAndroidApp, isIosApp } from "@web/core/browser/feature_detection";
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

    /**
     * @param {import("@web/env").OdooEnv} env
     * @param {Partial<import("services").Services>} services
     */
    async start(env, services) {
        const notification = services.notification;
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
            permission:
                isIosApp() || isAndroidApp()
                    ? "denied"
                    : this._normalizePermission(
                          permission?.state ?? browser.Notification?.permission
                      ),
            requestPermission: async () => {
                if (browser.Notification && state.permission === "prompt") {
                    state.permission = this._normalizePermission(
                        await browser.Notification.requestPermission()
                    );
                    if (state.permission === "denied") {
                        notification.add(_t("Odoo will not send notifications on this device."), {
                            type: "warning",
                            title: _t("Notifications blocked"),
                        });
                    } else if (state.permission === "granted") {
                        notification.add(_t("Odoo will send notifications on this device!"), {
                            type: "success",
                            title: _t("Notifications allowed"),
                        });
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
