import { fields, Record } from "@mail/core/common/record";

export class DiscussChannel extends Record {
    static _name = "discuss.channel";
    static _inherits = { "mail.thread": "thread" };
    static id = "id";

    static new() {
        const channel = super.new(...arguments);
        // ensure thread is set before reading/writing any other field
        channel.thread = { id: channel.id, model: "discuss.channel" };
        return channel;
    }

    /** @type {number} */
    id;
    thread = fields.One("mail.thread", {
        inverse: "channel",
        onDelete: (r) => r.delete(),
    });
    /** @type {number|undefined} */
    get member_count() {
        return this.thread.member_count;
    }
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
        if (correspondents?.length === 0 && this.channel_member_ids?.length === 1) {
            // Self-chat.
            return this.channel_member_ids[0];
        }
        return undefined;
    }
    correspondentCountry = fields.One("res.country", {
        /** @this {import("models").Thread} */
        compute() {
            return this.correspondent?.persona?.country_id ?? this.thread?.country_id;
        },
    });

    /** @returns {import("models").ChannelMember[]} */
    get correspondents() {
        return this.channel_member_ids?.filter(({ persona }) => persona?.notEq(this.store.self));
    }

    get showCorrespondentCountry() {
        return false;
    }

    get areAllMembersLoaded() {
        return this.member_count === this.channel_member_ids.length;
    }
}

DiscussChannel.register();
