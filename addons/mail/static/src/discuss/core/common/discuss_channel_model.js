import { fields, Record } from "@mail/core/common/record";

export class DiscussChannel extends Record {
    static _name = "discuss.channel";
    static _inherits = { "mail.thread": "thread" };
    static id = "id";

    /** @type {number} */
    id = fields.Attr(undefined, {
        onUpdate() {
            const busService = this.store.env.services.bus_service;
            if (!busService.isActive && !this.isTransient) {
                busService.start();
            }
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
    thread = fields.One("mail.thread", {
        compute() {
            return { id: this.id, model: "discuss.channel" };
        },
        inverse: "channel",
        onDelete: (r) => r?.delete(),
    });

    /**
     * @returns {boolean} true if the channel was opened, false otherwise
     */
    openChannel() {
        return false;
    }
}

DiscussChannel.register();
