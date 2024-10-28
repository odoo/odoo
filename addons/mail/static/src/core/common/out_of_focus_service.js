import { htmlToTextContentInline } from "@mail/utils/common/format";

import { browser } from "@web/core/browser/browser";
import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import { url } from "@web/core/utils/urls";

const PREVIEW_MSG_MAX_SIZE = 350; // optimal for native English speakers

/**
 * @typedef {Messaging} Messaging
 */
export class OutOfFocusService {
    /**
     * @param {import("@web/env").OdooEnv} env
     * @param {Partial<import("services").Services>} services
     */
    constructor(env, services) {
        this.setup(env, services);
    }

    setup(env, services) {
        this.env = env;
        this.audio = undefined;
        this.multiTab = services.multi_tab;
        this.notificationService = services.notification;
        this.closeFuncs = [];
    }

    async notify(message, thread) {
        const modelsHandleByPush = ["mail.thread", "discuss.channel"];
        if (
            modelsHandleByPush.includes(message.thread?.model) &&
            (await this.hasServiceWorkInstalledAndPushSubscriptionActive())
        ) {
            return;
        }
        const author = message.author;
        let notificationTitle;
        if (!author) {
            notificationTitle = _t("New message");
        } else {
            if (message.thread?.channel_type === "channel") {
                notificationTitle = _t("%(author name)s from %(channel name)s", {
                    "author name": author.name,
                    "channel name": message.thread.displayName,
                });
            } else {
                notificationTitle = author.name;
            }
        }
        const notificationContent = htmlToTextContentInline(message.body).substring(
            0,
            PREVIEW_MSG_MAX_SIZE
        );
        this.sendNotification({
            message: notificationContent,
            sound: message.thread?.model === "discuss.channel",
            title: notificationTitle,
            type: "info",
        });
    }

    async hasServiceWorkInstalledAndPushSubscriptionActive() {
        const registration = await browser.navigator.serviceWorker?.getRegistration();
        if (registration) {
            const pushManager = await registration.pushManager;
            if (pushManager) {
                const subscription = await pushManager.getSubscription();
                return !!subscription;
            }
        }
        return false;
    }

    /**
     * Send a notification, preferably a native one. If native
     * notifications are disable or unavailable on the current
     * platform, fallback on the notification service.
     *
     * @param {Object} param0
     * @param {string} [param0.message] The body of the
     * notification.
     * @param {string} [param0.title] The title of the notification.
     * @param {string} [param0.type] The type to be passed to the no
     * service when native notifications can't be sent.
     */
    sendNotification({ message, sound = true, title, type }) {
        if (!this.canSendNativeNotification) {
            this.sendOdooNotification(message, { sound, title, type });
            return;
        }
        if (!this.multiTab.isOnMainTab()) {
            return;
        }
        try {
            this.sendNativeNotification(title, message, { sound });
        } catch (error) {
            // Notification without Serviceworker in Chrome Android doesn't works anymore
            // So we fallback to the notification service in this case
            // https://bugs.chromium.org/p/chromium/issues/detail?id=481856
            if (error.message.includes("ServiceWorkerRegistration")) {
                this.sendOdooNotification(message, { sound, title, type });
            } else {
                throw error;
            }
        }
    }

    /**
     * @param {string} message
     * @param {Object} options
     */
    async sendOdooNotification(message, options) {
        const { sound } = options;
        delete options.sound;
        this.closeFuncs.push(this.notificationService.add(message, options));
        if (this.closeFuncs.length > 3) {
            this.closeFuncs.shift()();
        }
        if (sound) {
            this._playSound();
        }
    }

    /**
     * @param {string} title
     * @param {string} message
     */
    sendNativeNotification(title, message, { sound = true } = {}) {
        const notification = new Notification(title, {
            body: message,
            icon: "/mail/static/src/img/odoobot_transparent.png",
        });
        notification.addEventListener("click", ({ target: notification }) => {
            window.focus();
            notification.close();
        });
        if (sound) {
            this._playSound();
        }
    }

    async _playSound() {
        if (this.canPlayAudio && this.multiTab.isOnMainTab()) {
            if (!this.audio) {
                this.audio = new Audio();
                this.audio.src = this.audio.canPlayType("audio/ogg; codecs=vorbis")
                    ? url("/mail/static/src/audio/ting.ogg")
                    : url("/mail/static/src/audio/ting.mp3");
            }
            try {
                await this.audio.play();
            } catch {
                // Ignore errors due to the user not having interracted
                // with the page before playing the sound.
            }
        }
    }

    get canPlayAudio() {
        return typeof Audio !== "undefined";
    }

    get canSendNativeNotification() {
        return Boolean(browser.Notification && browser.Notification.permission === "granted");
    }
}

export const outOfFocusService = {
    dependencies: ["multi_tab", "notification"],
    /**
     * @param {import("@web/env").OdooEnv} env
     * @param {Partial<import("services").Services>} services
     */
    start(env, services) {
        const service = new OutOfFocusService(env, services);
        return service;
    },
};

registry.category("services").add("mail.out_of_focus", outOfFocusService);
