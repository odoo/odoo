import { Thread } from "@mail/core/common/thread_model";

/** @type {ReturnType<import("@mail/utils/common/misc").rpcWithEnv>} */
let rpc;
import { patch } from "@web/core/utils/patch";
import { imageUrl } from "@web/core/utils/urls";
import { _t } from "@web/core/l10n/translation";
import { rpcWithEnv } from "@mail/utils/common/misc";
import { Mutex } from "@web/core/utils/concurrency";
import { registry } from "@web/core/registry";

const commandRegistry = registry.category("discuss.channel_commands");

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
        return this.fetchChannelMutex.exec(async () => {
            if (!(this.localId in this.store.Thread.records)) {
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
    async fetchMoreAttachments(limit = 30) {
        if (this.isLoadingAttachments || this.areAttachmentsLoaded) {
            return;
        }
        this.isLoadingAttachments = true;
        try {
            const rawAttachments = await rpc("/discuss/channel/attachments", {
                before: Math.min(...this.attachments.map(({ id }) => id)),
                channel_id: this.id,
                limit,
            });
            const attachments = this.store.Attachment.insert(rawAttachments);
            if (attachments.length < limit) {
                this.areAttachmentsLoaded = true;
            }
        } finally {
            this.isLoadingAttachments = false;
        }
    },
    incrementUnreadCounter() {
        this.message_unread_counter++;
    },
    async mute({ minutes = false } = {}) {
        await rpc("/discuss/channel/mute", { channel_id: this.id, minutes });
    },
    /** @param {string} body */
    async post(body) {
        if (this.model === "discuss.channel" && body.startsWith("/")) {
            const [firstWord] = body.substring(1).split(/\s/);
            const command = commandRegistry.get(firstWord, false);
            if (
                command &&
                (!command.channel_types || command.channel_types.includes(this.channel_type))
            ) {
                await this.executeCommand(command, body);
                return;
            }
        }
        return super.post(...arguments);
    },
    async updateCustomNotifications(custom_notifications) {
        // Update the UI instantly to provide a better UX (no need to wait for the RPC to finish).
        this.custom_notifications = custom_notifications;
        await rpc("/discuss/channel/update_custom_notifications", {
            channel_id: this.id,
            custom_notifications,
        });
    },
};
patch(Thread, {
    new(...args) {
        rpc = rpcWithEnv(this.env);
        return super.new(...args);
    },
});
patch(Thread.prototype, threadPatch);
