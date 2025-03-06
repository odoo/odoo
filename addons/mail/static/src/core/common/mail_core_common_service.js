import { reactive } from "@odoo/owl";
import { loadEmoji, loader } from "@web/core/emoji_picker/emoji_picker";

import { registry } from "@web/core/registry";

export class MailCoreCommon {
    /**
     * @param {import("@web/env").OdooEnv} env
     * @param {import("services").ServiceFactories} services
     */
    constructor(env, services) {
        this.env = env;
        this.busService = services.bus_service;
        this.store = services["mail.store"];
        /** @type {{ [codepoints: string]: string[] }} */
        this.shortcodesByCodepoints = {};
        /** @type {RegExp|undefined} */
        this.knownEmojisRegex;
    }

    setup() {
        loader.onEmojiLoaded(async () => {
            const { emojis } = await loadEmoji();
            emojis.forEach((e) => (this.shortcodesByCodepoints[e.codepoints] = e.shortcodes));
            this.knownEmojisRegex = new RegExp(
                Object.keys(this.shortcodesByCodepoints)
                    .map((c) => c.replace(/[-/\\^$*+?.()|[\]{}]/g, "\\$&"))
                    .sort((a, b) => b.length - a.length) // Sort to get composed emojis first
                    .join("|"),
                "gu"
            );
        });
        this.busService.subscribe("ir.attachment/delete", (payload) => {
            const { id: attachmentId, message: messageData } = payload;
            if (messageData) {
                this.store["mail.message"].insert(messageData);
            }
            const attachment = this.store["ir.attachment"].get(attachmentId);
            attachment?.delete();
        });
        this.busService.subscribe("mail.message/delete", (payload, { id: notifId }) => {
            for (const messageId of payload.message_ids) {
                const message = this.store["mail.message"].get(messageId);
                if (!message) {
                    continue;
                }
                this.env.bus.trigger("mail.message/delete", { message, notifId });
                message.delete();
            }
        });
        this.busService.subscribe("mail.message/toggle_star", (payload, metadata) =>
            this._handleNotificationToggleStar(payload, metadata)
        );
        this.busService.subscribe("res.users.settings", (payload) => {
            if (payload) {
                this.store.settings.update(payload);
            }
        });
        this.busService.subscribe("mail.record/insert", (payload) => {
            this.store.insert(payload, { html: true });
        });
    }

    _handleNotificationToggleStar(payload, metadata) {
        const { message_ids: messageIds, starred } = payload;
        this.store["mail.message"].insert(messageIds.map((id) => ({ id, starred })));
    }
}

export const mailCoreCommon = {
    dependencies: ["bus_service", "mail.store"],
    /**
     * @param {import("@web/env").OdooEnv} env
     * @param {import("services").ServiceFactories} services
     */
    start(env, services) {
        const mailCoreCommon = reactive(new MailCoreCommon(env, services));
        mailCoreCommon.setup();
        return mailCoreCommon;
    },
};

registry.category("services").add("mail.core.common", mailCoreCommon);
