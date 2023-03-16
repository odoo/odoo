/* @odoo-module */

import { browser } from "@web/core/browser/browser";
import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import { escape, sprintf } from "@web/core/utils/strings";
import { url } from "@web/core/utils/urls";
import { htmlToTextContentInline } from "../utils/format";

const PREVIEW_MSG_MAX_SIZE = 350; // optimal for native English speakers

/**
 * @typedef {Messaging} Messaging
 */
export class OutOfFocusService {
    constructor(env, services) {
        this.env = env;
        this.audio = new Audio();
        this.audio.src = this.audio.canPlayType("audio/ogg; codecs=vorbis")
            ? url("/mail/static/src/audio/ting.ogg")
            : url("/mail/static/src/audio/ting.mp3");
        this.counter = 0;
        this.multiTab = services.multi_tab;
        this.busService = services.bus_service;
        this.notificationService = services.notification;
        this.busService.addEventListener("window_focus", () => {
            this.counter = 0;
            this.busService.trigger("set_title_part", {
                part: "_chat",
            });
        });
    }

    notify(message, channel) {
        const author = message.author;
        let notificationTitle;
        if (!author) {
            notificationTitle = _t("New message");
        } else {
            if (channel.channel_type === "channel") {
                notificationTitle = sprintf(_t("%(author name)s from %(channel name)s"), {
                    "author name": author.name,
                    "channel name": channel.displayName,
                });
            } else {
                notificationTitle = author.name;
            }
        }
        const notificationContent = escape(
            htmlToTextContentInline(message.body).substr(0, PREVIEW_MSG_MAX_SIZE)
        );
        this.sendNotification({
            message: notificationContent,
            title: notificationTitle,
            type: "info",
        });
        this.counter++;
        const titlePattern = this.counter === 1 ? _t("%s Message") : _t("%s Messages");
        this.busService.trigger("set_title_part", {
            part: "_chat",
            title: sprintf(titlePattern, this.counter),
        });
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
    sendNotification({ message, title, type }) {
        if (!this.canSendNativeNotification) {
            this.sendOdooNotification(message, { title, type });
            return;
        }
        if (!this.multiTab.isOnMainTab()) {
            return;
        }
        try {
            this.sendNativeNotification(title, message);
        } catch (error) {
            // Notification without Serviceworker in Chrome Android doesn't works anymore
            // So we fallback to the notification service in this case
            // https://bugs.chromium.org/p/chromium/issues/detail?id=481856
            if (error.message.includes("ServiceWorkerRegistration")) {
                this.sendOdooNotification(message, { title, type });
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
        this.notificationService.add(message, options);
        if (this.canPlayAudio && this.multiTab.isOnMainTab()) {
            try {
                await this.audio.play();
            } catch {
                // Ignore errors due to the user not having interracted
                // with the page before playing the sound.
            }
        }
    }

    /**
     * @param {string} title
     * @param {string} message
     */
    sendNativeNotification(title, message) {
        const notification = new Notification(
            // The native Notification API works with plain text and not HTML
            // unescaping is safe because done only at the **last** step
            _.unescape(title),
            {
                body: _.unescape(message),
                icon: "/mail/static/src/img/odoobot_transparent.png",
            }
        );
        notification.addEventListener("click", ({ target: notification }) => {
            window.focus();
            notification.close();
        });
    }

    get canPlayAudio() {
        return typeof Audio !== "undefined";
    }

    get canSendNativeNotification() {
        return Boolean(browser.Notification && browser.Notification.permission === "granted");
    }
}

export const outOfFocusService = {
    dependencies: ["bus_service", "multi_tab", "notification"],
    start(env, services) {
        const service = new OutOfFocusService(env, services);
        return service;
    },
};

registry.category("services").add("mail.out_of_focus", outOfFocusService);
