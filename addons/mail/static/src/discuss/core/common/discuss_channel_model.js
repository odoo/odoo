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
    id = fields.Attr(undefined, {
        onUpdate() {
            const busService = this.store.env.services.bus_service;
            if (!busService.isActive && !this.thread.isTransient) {
                busService.start();
            }
        },
    });
    thread = fields.One("mail.thread", {
        inverse: "channel",
        onDelete: (r) => r.delete(),
    });
}

DiscussChannel.register();
