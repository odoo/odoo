import { fields, Record } from "@mail/core/common/record";

export class DiscussChannel extends Record {
    static _name = "discuss.channel";
    static id = "id";

    /** @type {number} */
    id;
    get channel_member_ids() {
        return this.thread.channel_member_ids;
    }
    thread = fields.One("Thread", {
        inverse: "channel",
        onDelete: (r) => r.delete(),
    });
}

DiscussChannel.register();
