import { fields, Record } from "@mail/core/common/record";

export class DiscussChannel extends Record {
    static _name = "discuss.channel";
    static id = "id";

    /** @type {number} */
    id;

    thread = fields.One("Thread", {
        inverse: "channel",
        onDelete: (r) => r.delete(),
    });
    channel_member_ids = fields.Many("discuss.channel.member", {
        sort: (m1, m2) => m1.id - m2.id,
    });
    self_member_id = fields.One("discuss.channel.member");
    /** @type {number|undefined} */
    member_count = undefined;
    typingMembers = fields.Many("discuss.channel.member");

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
}

DiscussChannel.register();
