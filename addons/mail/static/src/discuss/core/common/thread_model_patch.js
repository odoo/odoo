import { Record } from "@mail/core/common/record";
import { Thread } from "@mail/core/common/thread_model";
import { compareDatetime, nearestGreaterThanOrEqual } from "@mail/utils/common/misc";

import { formatList } from "@web/core/l10n/utils";
import { rpc } from "@web/core/network/rpc";
import { registry } from "@web/core/registry";
import { Mutex } from "@web/core/utils/concurrency";
import { patch } from "@web/core/utils/patch";
import { imageUrl } from "@web/core/utils/urls";

const commandRegistry = registry.category("discuss.channel_commands");

/** @type {import("models").Thread} */
const threadPatch = {
    setup() {
        super.setup();
        this.channel_member_ids = Record.many("discuss.channel.member", {
            inverse: "thread",
            onDelete: (r) => r.delete(),
            sort: (m1, m2) => m1.id - m2.id,
        });
        this.correspondent = Record.one("discuss.channel.member", {
            /** @this {import("models").Thread} */
            compute() {
                return this.computeCorrespondent();
            },
        });
        this.default_display_mode = undefined;
        this.fetchChannelMutex = new Mutex();
        this.fetchChannelInfoDeferred = undefined;
        this.fetchChannelInfoState = "not_fetched";
        this.hasOtherMembersTyping = Record.attr(false, {
            /** @this {import("models").Thread} */
            compute() {
                return this.otherTypingMembers.length > 0;
            },
        });
        this.hasSeenFeature = Record.attr(false, {
            /** @this {import("models").Thread} */
            compute() {
                return this.store.channel_types_with_seen_infos.includes(this.channel_type);
            },
        });
        this.firstUnreadMessage = Record.one("mail.message", {
            /** @this {import("models").Thread} */
            compute() {
                if (!this.selfMember) {
                    return null;
                }
                const messages = this.messages;
                const separator = this.selfMember.localNewMessageSeparator;
                if (separator === 0 && !this.loadOlder) {
                    return messages[0];
                }
                if (!separator || messages.length === 0 || messages.at(-1).id < separator) {
                    return null;
                }
                // try to find a perfect match according to the member's separator
                let message = this.store["mail.message"].get({ id: separator });
                if (!message || this.notEq(message.thread)) {
                    message = nearestGreaterThanOrEqual(messages, separator, (msg) => msg.id);
                }
                return message;
            },
            inverse: "threadAsFirstUnread",
        });
        this.invitedMembers = Record.many("discuss.channel.member");
        this.last_interest_dt = Record.attr(undefined, { type: "datetime" });
        /** @type {luxon.DateTime} */
        this.lastInterestDt = Record.attr(undefined, {
            type: "datetime",
            /** @this {import("models").Thread} */
            compute() {
                const selfMemberLastInterestDt = this.selfMember?.last_interest_dt;
                const lastInterestDt = this.last_interest_dt;
                return compareDatetime(selfMemberLastInterestDt, lastInterestDt) > 0
                    ? selfMemberLastInterestDt
                    : lastInterestDt;
            },
        });
        this.lastMessageSeenByAllId = Record.attr(undefined, {
            /** @this {import("models").Thread} */
            compute() {
                if (!this.hasSeenFeature) {
                    return;
                }
                return this.channel_member_ids.reduce((lastMessageSeenByAllId, member) => {
                    if (member.persona.notEq(this.store.self) && member.seen_message_id) {
                        return lastMessageSeenByAllId
                            ? Math.min(lastMessageSeenByAllId, member.seen_message_id.id)
                            : member.seen_message_id.id;
                    }
                }, undefined);
            },
        });
        this.lastSelfMessageSeenByEveryone = Record.one("mail.message", {
            compute() {
                if (!this.lastMessageSeenByAllId) {
                    return false;
                }
                let res;
                // starts from most recent persistent messages to find early
                for (let i = this.persistentMessages.length - 1; i >= 0; i--) {
                    const message = this.persistentMessages[i];
                    if (!message.isSelfAuthored) {
                        continue;
                    }
                    if (message.id > this.lastMessageSeenByAllId) {
                        continue;
                    }
                    res = message;
                    break;
                }
                return res;
            },
        });
        this.member_count = undefined;
        /** @type {string} name: only for channel. For generic thread, @see display_name */
        this.name = undefined;
        this.onlineMembers = Record.many("discuss.channel.member", {
            /** @this {import("models").Thread} */
            compute() {
                return this.channel_member_ids
                    .filter((member) =>
                        this.store.onlineMemberStatuses.includes(member.persona.im_status)
                    )
                    .sort((m1, m2) => this.store.sortMembers(m1, m2)); // FIXME: sort are prone to infinite loop (see test "Display livechat custom name in typing status")
            },
        });
        this.offlineMembers = Record.many("discuss.channel.member", {
            compute() {
                return this._computeOfflineMembers().sort(
                    (m1, m2) => this.store.sortMembers(m1, m2) // FIXME: sort are prone to infinite loop (see test "Display livechat custom name in typing status")
                );
            },
        });
        this.otherTypingMembers = Record.many("discuss.channel.member", {
            /** @this {import("models").Thread} */
            compute() {
                return this.typingMembers.filter((member) => !member.persona?.eq(this.store.self));
            },
        });
        this.selfMember = Record.one("discuss.channel.member", {
            inverse: "threadAsSelf",
        });
        this.scrollUnread = true;
        this.toggleBusSubscription = Record.attr(false, {
            /** @this {import("models").Thread} */
            compute() {
                return (
                    this.model === "discuss.channel" &&
                    this.selfMember?.memberSince >= this.store.env.services.bus_service.startedAt
                );
            },
            onUpdate() {
                this.store.updateBusSubscription();
            },
        });
        this.typingMembers = Record.many("discuss.channel.member", { inverse: "threadAsTyping" });
    },
    _computeOfflineMembers() {
        return this.channel_member_ids.filter(
            (member) => !this.store.onlineMemberStatuses.includes(member.persona?.im_status)
        );
    },
    get areAllMembersLoaded() {
        return this.member_count === this.channel_member_ids.length;
    },
    get avatarUrl() {
        if (this.channel_type === "channel" || this.channel_type === "group") {
            return imageUrl("discuss.channel", this.id, "avatar_128", {
                unique: this.avatar_cache_key,
            });
        }
        if (this.channel_type === "chat" && this.correspondent) {
            return this.correspondent.persona.avatarUrl;
        }
        return super.avatarUrl;
    },
    computeCorrespondent() {
        if (this.channel_type === "channel") {
            return undefined;
        }
        const correspondents = this.correspondents;
        if (correspondents.length === 1) {
            // 2 members chat.
            return correspondents[0];
        }
        if (correspondents.length === 0 && this.channel_member_ids.length === 1) {
            // Self-chat.
            return this.channel_member_ids[0];
        }
        return undefined;
    },
    get correspondents() {
        return this.channel_member_ids.filter(({ persona }) => persona.notEq(this.store.self));
    },
    get displayName() {
        if (this.channel_type === "chat" && this.correspondent) {
            return this.custom_channel_name || this.correspondent.persona.name;
        }
        if (this.channel_type === "group" && !this.name) {
            return formatList(
                this.channel_member_ids.map((channelMember) => channelMember.persona.name)
            );
        }
        if (this.model === "discuss.channel" && this.name) {
            return this.name;
        }
        return super.displayName;
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
    async fetchChannelMembers() {
        if (this.fetchMembersState === "pending") {
            return;
        }
        const previousState = this.fetchMembersState;
        this.fetchMembersState = "pending";
        const known_member_ids = this.channel_member_ids.map((channelMember) => channelMember.id);
        let data;
        try {
            data = await rpc("/discuss/channel/members", {
                channel_id: this.id,
                known_member_ids: known_member_ids,
            });
        } catch (e) {
            this.fetchMembersState = previousState;
            throw e;
        }
        this.fetchMembersState = "fetched";
        this.store.insert(data);
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
            const { "ir.attachment": attachments = [] } = this.store.insert(data);
            if (attachments.length < limit) {
                this.areAttachmentsLoaded = true;
            }
        } finally {
            this.isLoadingAttachments = false;
        }
    },
    get hasMemberList() {
        return ["channel", "group"].includes(this.channel_type);
    },
    get hasSelfAsMember() {
        return Boolean(this.selfMember);
    },
    /** @override */
    get importantCounter() {
        if (this.isChatChannel && this.selfMember?.message_unread_counter) {
            return this.selfMember.totalUnreadMessageCounter;
        }
        return super.importantCounter;
    },
    /** @override */
    isDisplayedOnUpdate() {
        super.isDisplayedOnUpdate(...arguments);
        if (this.selfMember && !this.isDisplayed) {
            this.selfMember.syncUnread = true;
        }
    },
    get isUnread() {
        return this.selfMember?.message_unread_counter > 0 || super.isUnread;
    },
    /**
     * @override
     * @param {Object} [options]
     * @param {boolean} [options.sync] Whether to sync the unread message
     * state with the server values.
     */
    markAsRead({ sync } = {}) {
        super.markAsRead(...arguments);
        if (!this.selfMember) {
            return;
        }
        const newestPersistentMessage = this.newestPersistentOfAllMessage;
        if (!newestPersistentMessage) {
            return;
        }
        const alreadyReadBySelf =
            this.selfMember.seen_message_id?.id >= newestPersistentMessage.id &&
            this.selfMember.new_message_separator > newestPersistentMessage.id;
        if (alreadyReadBySelf) {
            // Server is up to date, but local state must be updated as well.
            this.selfMember.syncUnread = sync ?? this.selfMember.syncUnread;
            return;
        }
        rpc("/discuss/channel/mark_as_read", {
            channel_id: this.id,
            last_message_id: newestPersistentMessage.id,
            sync,
        }).catch((e) => {
            if (e.code !== 404) {
                throw e;
            }
        });
    },
    /**
     * To be overridden.
     * The purpose is to exclude technical channel_member_ids like bots and avoid
     * "wrong" seen message indicator
     */
    get membersThatCanSeen() {
        return this.channel_member_ids;
    },
    /** @override */
    get needactionCounter() {
        return this.isChatChannel
            ? this.selfMember?.message_unread_counter ?? 0
            : super.needactionCounter;
    },
    get notifyOnLeave() {
        // Skip notification if display name is unknown (might depend on
        // knowledge of members for groups).
        return Boolean(this.displayName);
    },
    /** @override */
    onNewSelfMessage(message) {
        if (!this.selfMember || message.id < this.selfMember.seen_message_id?.id) {
            return;
        }
        this.selfMember.syncUnread = true;
        this.selfMember.seen_message_id = message;
        this.selfMember.new_message_separator = message.id + 1;
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
    get showUnreadBanner() {
        return !this.selfMember?.hideUnreadBanner && this.selfMember?.localMessageUnreadCounter > 0;
    },
    get unknownMembersCount() {
        return (this.member_count ?? 0) - this.channel_member_ids.length;
    },
};
patch(Thread.prototype, threadPatch);
