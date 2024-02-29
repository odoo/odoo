/* @odoo-module */

import { Thread } from "@mail/core/common/thread_model";
import { assignDefined } from "@mail/utils/common/misc";

import { rpc } from "@web/core/network/rpc";
import { Mutex } from "@web/core/utils/concurrency";
import { patch } from "@web/core/utils/patch";
import { url } from "@web/core/utils/urls";
import { _t } from "@web/core/l10n/translation";

/** @type {import("models").Thread} */
const threadPatch = {
    setup() {
        super.setup();
        this.fetchChannelMutex = new Mutex();
        this.fetchChannelInfoDeferred = undefined;
        this.fetchChannelInfoState = "not_fetched";
    },
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
            const urlParams = assignDefined({}, { unique: this.avatarCacheKey });
            return url("/web/image", {
                field: "avatar_128",
                id: this.id,
                model: "discuss.channel",
                ...urlParams,
            });
        }
        if (this.type === "chat" && this.correspondent) {
            return this.correspondent.avatarUrl;
        }
        return super.avatarUrl;
    },
    async fetchChannelInfo() {
        return this.fetchChannelMutex.exec(async () => {
            if (!(this.localId in this._store.Thread.records)) {
                return; // channel was deleted in-between two calls
            }
            const data = await rpc("/discuss/channel/info", { channel_id: this.id });
            if (data) {
                this.update(data);
            } else {
                this.delete();
            }
            return data ? this : undefined;
        });
    },
    incrementUnreadCounter() {
        this.message_unread_counter++;
    },
};
patch(Thread.prototype, threadPatch);
