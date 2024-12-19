import { Record } from "@mail/core/common/record";
import { Thread } from "@mail/core/common/thread_model";
import { patch } from "@web/core/utils/patch";
import { imageUrl } from "@web/core/utils/urls";
import { rpc } from "@web/core/network/rpc";
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
        this.onlineMembers = Record.many("ChannelMember", {
            /** @this {import("models").Thread} */
            compute() {
                return this.channelMembers
                    .filter((member) =>
                        this.store.onlineMemberStatuses.includes(member.persona.im_status)
                    )
                    .sort((m1, m2) => this.store.sortMembers(m1, m2)); // FIXME: sort are prone to infinite loop (see test "Display livechat custom name in typing status")
            },
        });
        this.offlineMembers = Record.many("ChannelMember", {
            compute() {
                return this._computeOfflineMembers().sort(
                    (m1, m2) => this.store.sortMembers(m1, m2) // FIXME: sort are prone to infinite loop (see test "Display livechat custom name in typing status")
                );
            },
        });
    },
    _computeOfflineMembers() {
        return this.channelMembers.filter(
            (member) => !this.store.onlineMemberStatuses.includes(member.persona?.im_status)
        );
    },
    get avatarUrl() {
        if (this.channel_type === "channel" || this.channel_type === "group") {
            return imageUrl("discuss.channel", this.id, "avatar_128", {
                unique: this.avatarCacheKey,
            });
        }
        if (this.channel_type === "chat" && this.correspondent) {
            return this.correspondent.persona.avatarUrl;
        }
        return super.avatarUrl;
    },
    get hasMemberList() {
        return ["channel", "group"].includes(this.channel_type);
    },
    async fetchChannelInfo() {
        return this.fetchChannelMutex.exec(async () => {
            if (!(this.localId in this.store.Thread.records)) {
                return; // channel was deleted in-between two calls
            }
            const data = await rpc("/discuss/channel/info", { channel_id: this.id });
            if (data) {
                this.store.insert(data);
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
            const data = await rpc("/discuss/channel/attachments", {
                before: Math.min(...this.attachments.map(({ id }) => id)),
                channel_id: this.id,
                limit,
            });
            const { Attachment: attachments = [] } = this.store.insert(data);
            if (attachments.length < limit) {
                this.areAttachmentsLoaded = true;
            }
        } finally {
            this.isLoadingAttachments = false;
        }
    },
    get notifyOnLeave() {
        // Skip notification if display name is unknown (might depend on
        // knowledge of members for groups).
        return Boolean(this.displayName);
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
};
patch(Thread.prototype, threadPatch);
