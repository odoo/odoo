/* @odoo-module */

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
     *
     * @returns {"prompt" | "granted" | "denied"}
     * @private
     */
    _queryPermission() {
        if (isIosApp() || isAndroidApp()) {
            return "denied";
        }
        return this._normalizePermission(browser.Notification?.permission);
    },

    /**
     * @param {import("@web/env").OdooEnv} env
     * @param {Partial<import("services").Services>} services
     */
    async start(env, services) {
        const notification = services.notification;
        const state = reactive({
            /** @type {"prompt" | "granted" | "denied"} */
            permission: this._queryPermission(),
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

        try {
            const permission = await browser.navigator?.permissions?.query({
                name: "notifications",
            });
            if (permission) {
                permission.addEventListener("change", () => {
                    state.permission = this._queryPermission();
                });
            }
        } catch {
            // noop
        }

        return state;
    },
};

registry.category("services").add("mail.notification.permission", notificationPermissionService);
