// @ts-check
/** @odoo-module native */
import { onWillDestroy } from "@odoo/owl";
import { browser } from "@web/core/browser/browser";
import { makeLogger } from "@web/core/debug/debug_logger";
import { _t } from "@web/core/translation";
import { Mutex } from "@web/core/utils/concurrency";
import { useService } from "@web/core/utils/hooks";
import { patch } from "@web/core/utils/patch";
import { WebClient } from "@web/webclient/webclient";

const log = makeLogger("mail.push");
const USER_DEVICES_MODEL = "mail.push.device";

patch(WebClient.prototype, {
    setup() {
        super.setup();
        this.orm = useService("orm");
        this.notification = useService("notification");
        this.serviceWorker = useService("service_worker");
        this._pushMutex = new Mutex();
        this.env.services["mail.store"]?.initialize();
        if (this._canSendNativeNotification) {
            this.env.bus.addEventListener(
                "WEB_CLIENT_READY",
                () => this._subscribePush(),
                {
                    once: true,
                },
            );
        }
        if (browser.navigator.permissions) {
            let notificationPerm;
            const onPermissionChange = () => {
                log.logic("notification permission change", () => ({
                    permission: browser.Notification?.permission,
                }));
                if (this._canSendNativeNotification) {
                    this._subscribePush();
                } else {
                    this._unsubscribePush();
                }
            };
            browser.navigator.permissions
                .query({ name: "notifications" })
                .then((perm) => {
                    notificationPerm = perm;
                    notificationPerm.addEventListener("change", onPermissionChange);
                })
                .catch(() => {});
            onWillDestroy(() => {
                notificationPerm?.removeEventListener("change", onPermissionChange);
            });
        }
    },
    /** @returns {boolean} */
    get _canSendNativeNotification() {
        return browser.Notification?.permission === "granted";
    },

    /**
     * @param {number} [numberTry=1]
     * @returns {Promise<void>}
     */
    async _subscribePush(numberTry = 1) {
        return this._pushMutex.exec(() => this._doSubscribePush(numberTry));
    },

    /** @param {number} [numberTry=1] */
    async _doSubscribePush(numberTry = 1) {
        await this.serviceWorker.registrationSettled;
        const pushManager = await this.pushManager();
        if (!pushManager) {
            log.logic("subscribePush: no push manager");
            return;
        }
        let subscription = await pushManager.getSubscription();
        const previousEndpoint = browser.localStorage.getItem(
            `${USER_DEVICES_MODEL}_endpoint`,
        );
        log.pipeline("subscribePush", () => ({
            numberTry,
            hasSubscription: Boolean(subscription),
            hasPreviousEndpoint: Boolean(previousEndpoint),
        }));
        if (!subscription) {
            try {
                const applicationServerKey = await this._getApplicationServerKey();
                if (!applicationServerKey) {
                    log.logic("subscribePush: the server has no VAPID key");
                    return;
                }
                subscription = await pushManager.subscribe({
                    userVisibleOnly: true,
                    applicationServerKey,
                });
            } catch (error) {
                log.logic("pushManager.subscribe failed", () => ({
                    message: error?.message,
                }));
                console.warn(error);
                this.notification.add(error.message, {
                    title: _t("Failed to enable push notifications"),
                    type: "danger",
                    sticky: true,
                });
                if (await navigator.brave?.isBrave()) {
                    this.notification.add(
                        _t(
                            "Brave: enable 'Google Services for Push Messaging' to enable push notifications",
                        ),
                        {
                            type: "warning",
                            sticky: true,
                        },
                    );
                }
                return;
            }
        }
        /** @type {PushSubscriptionJSON & {previous_endpoint?: string, vapid_public_key?: string}} */
        const kwargs = subscription.toJSON();
        if (previousEndpoint && subscription.endpoint !== previousEndpoint) {
            kwargs.previous_endpoint = previousEndpoint;
        }
        try {
            kwargs.vapid_public_key = this._arrayBufferToBase64(
                subscription.options.applicationServerKey,
            );
            await this.orm.call(USER_DEVICES_MODEL, "register_devices", [], kwargs);
            browser.localStorage.setItem(
                `${USER_DEVICES_MODEL}_endpoint`,
                subscription.endpoint,
            );
            log.lifecycle("push device registered", () => ({
                endpointChanged: Boolean(kwargs.previous_endpoint),
            }));
        } catch (e) {
            log.logic("register_devices failed", () => ({
                name: e.data?.name,
                numberTry,
            }));
            const invalidVapidErrorClass =
                "odoo.addons.mail.tools.jwt.InvalidVapidError";
            const warningMessage =
                "Error sending subscription information to the server";
            if (e.data?.name === invalidVapidErrorClass) {
                const MAX_TRIES = 2;
                if (numberTry < MAX_TRIES) {
                    await subscription.unsubscribe();
                    await this._doSubscribePush(numberTry + 1);
                } else {
                    console.warn(warningMessage);
                }
            } else {
                console.warn(`${warningMessage}: ${e.data?.debug}`);
            }
        }
    },

    /** @return {Promise<void>} */
    async _unsubscribePush() {
        return this._pushMutex.exec(() => this._doUnsubscribePush());
    },

    async _doUnsubscribePush() {
        await this.serviceWorker.registrationSettled;
        const pushManager = await this.pushManager();
        if (!pushManager) {
            return;
        }
        const subscription = await pushManager.getSubscription();
        if (!subscription) {
            return;
        }
        log.lifecycle("unsubscribePush");
        await this.orm.call(USER_DEVICES_MODEL, "unregister_devices", [], {
            endpoint: subscription.endpoint,
        });
        await subscription.unsubscribe();
        browser.localStorage.removeItem(`${USER_DEVICES_MODEL}_endpoint`);
    },

    /** @return {Promise<PushManager>} */
    async pushManager() {
        const registration = await browser.navigator.serviceWorker?.getRegistration();
        return registration?.pushManager;
    },

    /** @return {Promise<Uint8Array<ArrayBuffer> | null>} */
    async _getApplicationServerKey() {
        const vapid_public_key_base64 = await this.orm.call(
            USER_DEVICES_MODEL,
            "get_or_create_web_push_vapid_public_key",
        );
        if (!vapid_public_key_base64) {
            return null;
        }
        const padding = "=".repeat((4 - (vapid_public_key_base64.length % 4)) % 4);
        const base64 = (vapid_public_key_base64 + padding)
            .replace(/-/g, "+")
            .replace(/_/g, "/");
        const rawData = atob(base64);
        const outputArray = new Uint8Array(rawData.length);
        for (let i = 0; i < rawData.length; ++i) {
            outputArray[i] = rawData.charCodeAt(i);
        }
        return outputArray;
    },

    /**
     * @param {ArrayBuffer} buffer
     * @return {string}
     */
    _arrayBufferToBase64(buffer) {
        const bytes = new Uint8Array(buffer);
        let binary = "";
        for (let i = 0; i < bytes.byteLength; i++) {
            binary += String.fromCharCode(bytes[i]);
        }
        return window
            .btoa(binary)
            .replaceAll("+", "-")
            .replaceAll("/", "_")
            .replaceAll("=", "");
    },
});
