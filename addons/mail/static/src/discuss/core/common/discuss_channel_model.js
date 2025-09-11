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
}

DiscussChannel.register();
