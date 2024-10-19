/** @odoo-module **/

import { browser } from "@web/core/browser/browser";
import { useService } from "@web/core/utils/hooks";
import { patch } from "@web/core/utils/patch";
import { WebClient } from "@web/webclient/webclient";
import { onWillDestroy } from "@odoo/owl";
import { _t } from "@web/core/l10n/translation";

const USER_DEVICES_MODEL = "mail.partner.device";

patch(WebClient.prototype, {
    /**
     * @override
     */
    setup() {
        super.setup();
        this.rpc = useService("rpc");
        this.orm = useService("orm");
        this.notification = useService("notification");
        if (this._canSendNativeNotification) {
            this._subscribePush();
        }
        if (browser.navigator.permissions) {
            let notificationPerm;
            const onPermissionChange = () => {
                if (this._canSendNativeNotification) {
                    this._subscribePush();
                } else {
                    this._unsubscribePush();
                }
            };
            browser.navigator.permissions.query({ name: "notifications" }).then((perm) => {
                notificationPerm = perm;
                notificationPerm.addEventListener("change", onPermissionChange);
            });
            onWillDestroy(() => {
                notificationPerm?.removeEventListener("change", onPermissionChange);
            });
        }
    },
    /**
     *
     * @returns {boolean}
     * @private
     */
    get _canSendNativeNotification() {
        return browser.Notification?.permission === "granted";
    },

    /**
     * Subscribe device from push notification
     *
     * @private
     * @return {Promise<void>}
     */
    async _subscribePush(numberTry = 1) {
        const pushManager = await this.pushManager();
        if (!pushManager) {
            return;
        }
        let subscription = await pushManager.getSubscription();
        const previousEndpoint = browser.localStorage.getItem(`${USER_DEVICES_MODEL}_endpoint`);
        // This may occur if the subscription was refreshed by the browser,
        // but it may also happen if the subscription has been revoked or lost.
        if (!subscription) {
            try {
                subscription = await pushManager.subscribe({
                    userVisibleOnly: true,
                    applicationServerKey: await this._getApplicationServerKey(),
                });
            } catch (error) {
                console.warn(error);
                this.notification.add(error.message, {
                    title: _t("Failed to enable push notifications"),
                    type: "danger",
                    sticky: true,
                });
                if (await navigator.brave?.isBrave()) {
                    this.notification.add(
                        _t(
                            "Brave: enable 'Google Services for Push Messaging' to enable push notifications"
                        ),
                        {
                            type: "warning",
                            sticky: true,
                        }
                    );
                }
                return;
            }
            browser.localStorage.setItem(`${USER_DEVICES_MODEL}_endpoint`, subscription.endpoint);
        }
        const kwargs = subscription.toJSON();
        if (previousEndpoint && subscription.endpoint !== previousEndpoint) {
            kwargs.previous_endpoint = previousEndpoint;
        }
        try {
            kwargs.vapid_public_key = this._arrayBufferToBase64(
                subscription.options.applicationServerKey
            );
            await this.orm.call(USER_DEVICES_MODEL, "register_devices", [], kwargs);
        } catch (e) {
            const invalidVapidErrorClass =
                "odoo.addons.mail.models.partner_devices.InvalidVapidError";
            const warningMessage = "Error sending subscription information to the server";
            if (e.data?.name === invalidVapidErrorClass) {
                const MAX_TRIES = 2;
                if (numberTry < MAX_TRIES) {
                    await subscription.unsubscribe();
                    this._subscribePush(numberTry + 1);
                } else {
                    console.warn(warningMessage);
                }
            } else {
                console.warn(`${warningMessage}: ${e.data?.debug}`);
            }
        }
    },

    /**
     * Unsubscribe device from push notification
     *
     * @private
     * @return {Promise<void>}
     */
    async _unsubscribePush() {
        const pushManager = await this.pushManager();
        if (!pushManager) {
            return;
        }
        const subscription = await pushManager.getSubscription();
        if (!subscription) {
            return;
        }
        await this.orm.call(USER_DEVICES_MODEL, "unregister_devices", [], {
            endpoint: subscription.endpoint,
        });
        await subscription.unsubscribe();
        browser.localStorage.removeItem(`${USER_DEVICES_MODEL}_endpoint`);
    },

    /**
     * Retrieve the PushManager interface of the Push API provides a way to receive notifications from third-party
     * servers as well as request URLs for push notifications.
     *
     * @return {Promise<PushManager>}
     */
    async pushManager() {
        const registration = await browser.navigator.serviceWorker?.getRegistration();
        return registration?.pushManager;
    },

    /**
     *
     * The Application Server Key is need to be an Uint8Array.
     * This format is used when the exchanging secret key between client and server.
     * This base64 to Uint8Array implementation is inspired by https://github.com/gbhasha/base64-to-uint8array
     *
     * @private
     * @return {Uint8Array}
     */
    async _getApplicationServerKey() {
        const vapid_public_key_base64 = await this.orm.call(
            USER_DEVICES_MODEL,
            "get_web_push_vapid_public_key"
        );
        const padding = "=".repeat((4 - (vapid_public_key_base64.length % 4)) % 4);
        const base64 = (vapid_public_key_base64 + padding).replace(/-/g, "+").replace(/_/g, "/");
        const rawData = atob(base64);
        const outputArray = new Uint8Array(rawData.length);
        for (let i = 0; i < rawData.length; ++i) {
            outputArray[i] = rawData.charCodeAt(i);
        }
        return outputArray;
    },

    /**
     * Convert an ArrayBuffer to a base64 string without padding
     * @param buffer {ArrayBuffer}
     * @return {string}
     * @private
     */
    _arrayBufferToBase64(buffer) {
        const bytes = new Uint8Array(buffer);
        let binary = "";
        for (let i = 0; i < bytes.byteLength; i++) {
            binary += String.fromCharCode(bytes[i]);
        }
        return window.btoa(binary).replaceAll("+", "-").replaceAll("/", "_").replaceAll("=", "");
    },
});
