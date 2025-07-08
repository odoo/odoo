import { Record, fields } from "@mail/core/common/record";
import { imageUrl } from "@web/core/utils/urls";
import { formatList } from "@web/core/l10n/utils";

export class Channel extends Record {
    static id = "id";
    static _name = "discuss.channel";

    /** @type {number} */
    id;
    thread = fields.One("Thread", { inverse: "channel" });
    /** @type {string} name: only for channel. For generic thread, @see display_name */
    name;
    channel_type;
    /** @type {number|undefined} */
    member_count = undefined;
    channel_member_ids = fields.Many("discuss.channel.member", {
        inverse: "channel_id",
        onDelete: (r) => r.delete(),
        sort: (m1, m2) => m1.id - m2.id,
    });
    selfMember = fields.One("discuss.channel.member", {
        inverse: "threadAsSelf",
    });
    typingMembers = fields.Many("discuss.channel.member", { inverse: "threadAsTyping" });
    hasOtherMembersTyping = fields.Attr(false, {
        /** @this {import("models").Thread} */
        compute() {
            return this.otherTypingMembers.length > 0;
        },
    });
    otherTypingMembers = fields.Many("discuss.channel.member", {
        /** @this {import("models").Thread} */
        compute() {
            return this.typingMembers.filter((member) => !member.persona?.eq(this.store.self));
        },
    });
    onlineMembers = fields.Many("discuss.channel.member", {
        /** @this {import("models").Thread} */
        compute() {
            return this.channel_member_ids
                .filter((member) =>
                    this.store.onlineMemberStatuses.includes(member.persona.im_status)
                )
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
            (member) => !this.store.onlineMemberStatuses.includes(member.persona?.im_status)
        );
    }
    get unknownMembersCount() {
        return (this.member_count ?? 0) - this.channel_member_ids.length;
    }
    get areAllMembersLoaded() {
        return this.member_count === this.channel_member_ids.length;
    }
    /** @returns {import("models").ChannelMember[]} */
    get correspondents() {
        console.log(this.channel_member_ids);
        return this.channel_member_ids.filter(({ persona }) => persona?.notEq(this.store.self));
    }
    /** @returns {import("models").ChannelMember} */
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
    }
    correspondent = fields.One("discuss.channel.member", {
        /** @this {import("models").Thread} */
        compute() {
            return this.computeCorrespondent();
        },
    });
    correspondentCountry = fields.One("res.country", {
        /** @this {import("models").Thread} */
        compute() {
            return this.correspondent?.persona?.country_id ?? this.country_id;
        },
    });
    get allowCalls() {
        return (
            !this.isTransient &&
            this.typesAllowingCalls.includes(this.channel_type) &&
            !this.correspondent?.persona.eq(this.store.odoobot)
        );
    }
    get avatarUrl() {
        if (this.channel_type === "channel" || this.channel_type === "group") {
            return imageUrl("discuss.channel", this.id, "avatar_128", {
                unique: this.avatar_cache_key,
            });
        }
        if (this.channel_type === "chat" && this.correspondent) {
            return this.correspondent.persona.avatarUrl;
        }
        return "";
    }
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
    get displayName() {
        if (this.supportsCustomChannelName && this.selfMember?.custom_channel_name) {
            return this.selfMember.custom_channel_name;
        }
        if (this.channel_type === "chat" && this.correspondent) {
            return this.correspondent.name;
        }
        if (this.channel_type === "group" && !this.name) {
            return formatList(this.channel_member_ids.map((channelMember) => channelMember.name));
        }
        return this.name;
    }
}

Channel.register();
