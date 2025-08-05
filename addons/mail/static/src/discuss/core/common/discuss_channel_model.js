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
}

DiscussChannel.register();
