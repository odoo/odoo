import { onWillStart, Plugin, signal, usePlugin } from "@odoo/owl";

import {
    isAndroidApp,
    isDisplayStandalone,
    isIOS,
    isIosApp,
} from "@web/core/browser/feature_detection";
import { _t } from "@web/core/l10n/translation";
import { NotificationPlugin } from "@web/core/notifications/notification_plugin";
import { services } from "@web/core/services";

async function getIosPwaPermission() {
    const registration = await window.navigator.serviceWorker?.getRegistration();
    return (await registration?.pushManager.permissionState()) ?? "prompt";
}

/** Records reach this plugin as `store.notificationPermission`. */
export class NotificationPermissionPlugin extends Plugin {
    #notification = usePlugin(NotificationPlugin);
    /** @type {import("@odoo/owl").Signal<"prompt" | "granted" | "denied">} */
    #permission = signal();

    setup() {
        onWillStart(async () => {
            let permission;
            try {
                if (isIOS() && isDisplayStandalone()) {
                    permission = { state: await getIosPwaPermission() };
                } else if (isIOS()) {
                    permission = { state: "denied" };
                } else {
                    permission = await window.navigator?.permissions?.query({
                        name: "notifications",
                    });
                }
            } catch {
                // noop
            }
            this.#permission.set(
                isIosApp() || isAndroidApp()
                    ? "denied"
                    : this._normalizePermission(
                          permission?.state ?? window.Notification?.permission
                      )
            );
            if (permission && !isIOS()) {
                permission.addEventListener("change", () => this.#permission.set(permission.state));
            }
        });
    }

    /** @type {"prompt" | "granted" | "denied"} */
    get permission() {
        return this.#permission();
    }

    _normalizePermission(permission) {
        switch (permission) {
            case "default":
                return "prompt";
            case undefined:
                return "denied";
            default:
                return permission;
        }
    }

    async requestPermission() {
        if (window.Notification && this.permission === "prompt") {
            this.#permission.set(
                this._normalizePermission(await window.Notification.requestPermission())
            );
            if (this.permission === "denied") {
                this.#notification.add(_t("Odoo will not send notifications on this device."), {
                    type: "warning",
                    title: _t("Notifications blocked"),
                });
            } else if (this.permission === "granted") {
                this.#notification.add(_t("Odoo will send notifications on this device!"), {
                    type: "success",
                    title: _t("Notifications allowed"),
                });
            }
        }
    }
}

services.add(NotificationPermissionPlugin);
