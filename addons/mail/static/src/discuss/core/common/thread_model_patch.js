import { Record } from "@mail/core/common/record";
import { Thread } from "@mail/core/common/thread_model";

import { rpc } from "@web/core/network/rpc";
import { Deferred } from "@web/core/utils/concurrency";
import { patch } from "@web/core/utils/patch";
import { imageUrl } from "@web/core/utils/urls";
import { _t } from "@web/core/l10n/translation";

/** @type {import("models").Thread} */
const threadPatch = {
    setup() {
        super.setup();
        this.fetchChannelInfoDeferred = undefined;
        this.fetchChannelInfoState = Record.attr("not_fetched", {
            /** @this {import("models").Thread} */
            onUpdate() {
                if (this.fetchChannelInfoState === "fetched") {
                    this._store.updateBusSubscription();
                }
            },
        });
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
        if (this.channel_type === "channel" || this.channel_type === "group") {
            return imageUrl("discuss.channel", this.id, "avatar_128", {
                unique: this.avatarCacheKey,
            });
        }
        if (this.channel_type === "chat" && this.correspondent) {
            return this.correspondent.avatarUrl;
        }
        return super.avatarUrl;
    },
    async fetchChannelInfo() {
        if (this.fetchChannelInfoState === "fetched") {
            return this.fetchChannelInfoDeferred ?? Promise.resolve(this);
        }
        if (this.fetchChannelInfoStateState === "fetching") {
            return this.fetchChannelInfoDeferred;
        }
        this.fetchChannelInfoState = "fetching";
        this.fetchChannelInfoDeferred = new Deferred();
        rpc("/discuss/channel/info", { channel_id: this.id }).then(
            (channelData) => {
                this.fetchChannelInfoState = "fetched";
                if (channelData) {
                    this._store.Thread.insert(channelData);
                } else {
                    this.delete();
                }
                this.fetchChannelInfoDeferred.resolve(channelData ? this : undefined);
            },
            (error) => {
                this.fetchChannelInfoState = "not_fetched";
                this.fetchChannelInfoDeferred.reject(error);
            }
        );
        return this.fetchChannelInfoDeferred;
    },
    incrementUnreadCounter() {
        this.message_unread_counter++;
    },
};
patch(Thread.prototype, threadPatch);
