/* @odoo-module */

import { Thread } from "@mail/core/common/thread_model";
import { assignDefined } from "@mail/utils/common/misc";

import { patch } from "@web/core/utils/patch";
import { url } from "@web/core/utils/urls";
import { _t } from "@web/core/l10n/translation";

patch(Thread.prototype, {
    get SETTINGS() {
        return [
            {
                id: false,
                name: _t("All Messages"),
            },
            {
                id: "mentions",
                name: _t("Mentions Only"),
            },
            {
                id: "no_notif",
                name: _t("Nothing"),
            },
        ];
    },
    get MUTES() {
        return [
            {
                id: "15_mins",
                value: 15,
                name: _t("For 15 minutes"),
            },
            {
                id: "1_hour",
                value: 60,
                name: _t("For 1 hour"),
            },
            {
                id: "3_hours",
                value: 180,
                name: _t("For 3 hours"),
            },
            {
                id: "8_hours",
                value: 480,
                name: _t("For 8 hours"),
            },
            {
                id: "24_hours",
                value: 1440,
                name: _t("For 24 hours"),
            },
            {
                id: "forever",
                value: -1,
                name: _t("Until I turn it back on"),
            },
        ];
    },
    get avatarUrl() {
        if (this.type === "channel" || this.type === "group") {
            return url(
                `/discuss/channel/${this.id}/avatar_128`,
                assignDefined({}, { unique: this.avatarCacheKey })
            );
        }
        if (this.type === "chat") {
            return this.correspondent.avatarUrl;
        }
        return super.avatarUrl;
    },
    async addNewMessage(message) {
        if (
            message.originThread.model === "discuss.channel" &&
            !message.originThread.channel_type
        ) {
            const channel = await this._store.env.services["mail.thread"].fetchChannel(
                message.originThread.id
            );
            if (!channel) {
                return;
            }
        }
        super.addNewMessage(...arguments);
        if (
            !message.originThread.correspondent?.eq(this._store.odoobot) &&
            message.originThread.channel_type !== "channel" &&
            this._store.self?.type === "partner"
        ) {
            // disabled on non-channel threads and
            // on "channel" channels for performance reasons
            this._store.env.services["mail.thread"].markAsFetched(message.originThread);
        }
    },
});
