import { fields, Record } from "@mail/core/common/record";

export class DiscussChannel extends Record {
    static _name = "discuss.channel";
    static _inherits = { Thread: "thread" };
    static id = "id";

    static new() {
        const channel = super.new(...arguments);
        // ensure thread is set before reading/writing any other field
        channel.thread = { id: channel.id, model: "discuss.channel" };
        return channel;
    }

    /** @type {number} */
    id;
    thread = fields.One("Thread", {
        inverse: "channel",
        onDelete: (r) => r.delete(),
    });
}

DiscussChannel.register();
