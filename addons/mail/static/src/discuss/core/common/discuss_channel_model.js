import { fields, Record } from "@mail/core/common/record";
import { imageUrl } from "@web/core/utils/urls";

export class DiscussChannel extends Record {
    static _name = "discuss.channel";
    static id = "id";

    /** @type {number} */
    id;
    /** @type {String} */
    avatar_cache_key;
    thread = fields.One("Thread", {
        inverse: "channel",
        onDelete: (r) => r.delete(),
    });
    channel_member_ids = fields.Many("discuss.channel.member", {
        sort: (m1, m2) => m1.id - m2.id,
    });
    country_id = fields.One("res.country");
    self_member_id = fields.One("discuss.channel.member");
    /** @type {number|undefined} */
    member_count = undefined;
    typingMembers = fields.Many("discuss.channel.member");
    firstUnreadMessage = fields.One("mail.message");
    default_display_mode;
    hasSeenFeature = fields.Attr(false, {
        /** @this {import("models").Thread} */
        compute() {
            return this.store.channel_types_with_seen_infos.includes(this.channel_type);
        },
    });
    lastMessageSeenByAllId = fields.Attr(undefined, {
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
                } else {
                    return lastMessageSeenByAllId;
                }
            }, undefined);
        },
    });
    lastSelfMessageSeenByEveryone = fields.One("mail.message", {
        compute() {
            if (!this.lastMessageSeenByAllId) {
                return false;
            }
            let res;
            // starts from most recent persistent messages to find early
            for (let i = this.thread.persistentMessages.length - 1; i >= 0; i--) {
                const message = this.thread.persistentMessages[i];
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

    correspondent = fields.One("discuss.channel.member", {
        /** @this {import("models").Thread} */
        compute() {
            return this.computeCorrespondent();
        },
    });
    /** @returns {import("models").ChannelMember} */
    computeCorrespondent() {
        if (this.channel_type === "channel") {
            return undefined;
        }
        const correspondents = this.correspondents;
        if (correspondents?.length === 1) {
            // 2 members chat.
            return correspondents[0];
        }
        if (correspondents?.length === 0 && this.channel_member_ids.length === 1) {
            // Self-chat.
            return this.channel_member_ids[0];
        }
        return undefined;
    }
    correspondentCountry = fields.One("res.country", {
        /** @this {import("models").Thread} */
        compute() {
            return this.correspondent?.persona?.country_id ?? this.country_id;
        },
    });

    /** @returns {import("models").ChannelMember[]} */
    get correspondents() {
        if (!this.channel_member_ids) {
            return [];
        }
        return this.channel_member_ids?.filter(({ persona }) => persona?.notEq(this.store.self));
    }

    get showCorrespondentCountry() {
        return false;
    }

    get areAllMembersLoaded() {
        return this.member_count === this.channel_member_ids.length;
    }

    onlineMembers = fields.Many("discuss.channel.member", {
        /** @this {import("models").Thread} */
        compute() {
            return this.channel_member_ids
                .filter((member) => this.store.onlineMemberStatuses.includes(member.im_status))
                .sort((m1, m2) => this.store.sortMembers(m1, m2)); // FIXME: sort are prone to infinite loop (see test "Display livechat custom name in typing status")
        },
    });

    offlineMembers = fields.Many("discuss.channel.member", {
        compute() {
            return this._computeOfflineMembers().sort(
                (m1, m2) => this.store.sortMembers(m1, m2) // FIXME: sort are prone to infinite loop (see test "Display livechat custom name in typing status")
            );
        },
    });

    /** @returns {import("models").ChannelMember[]} */
    _computeOfflineMembers() {
        return this.channel_member_ids.filter(
            (member) => !this.store.onlineMemberStatuses.includes(member.im_status)
        );
    }

    get hasSelfAsMember() {
        return Boolean(this.self_member_id);
    }

    get hasMemberList() {
        return ["channel", "group"].includes(this.channel_type);
    }
    otherTypingMembers = fields.Many("discuss.channel.member", {
        /** @this {import("models").Thread} */
        compute() {
            return this.typingMembers.filter((member) => !member.persona?.eq(this.store.self));
        },
    });
    hasOtherMembersTyping = fields.Attr(false, {
        /** @this {import("models").Thread} */
        compute() {
            return this.otherTypingMembers.length > 0;
        },
    });

    get avatarUrl() {
        if (this.channel_type === "channel" || this.channel_type === "group") {
            return imageUrl("discuss.channel", this.id, "avatar_128", {
                unique: this.avatar_cache_key,
            });
        }
        return this.correspondent?.avatarUrl;
    }
    /**
     * To be overridden.
     * The purpose is to exclude technical channel_member_ids like bots and avoid
     * "wrong" seen message indicator
     * @returns {import("models").ChannelMember[]}
     */
    get membersThatCanSeen() {
        return this.channel_member_ids;
    }
}

DiscussChannel.register();
