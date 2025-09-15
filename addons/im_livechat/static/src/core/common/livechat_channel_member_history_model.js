import { fields, Record } from "@mail/core/common/record";

export class LivechatChannelMemberHistory extends Record {
    static id = "id";
    static _name = "im_livechat.channel.member.history";

    channel_id = fields.One("Thread");
    guest_id = fields.One("mail.guest");
    /** @type {number} */
    id;
    /** @type {"agent"|"visitor"|"bot"} */
    livechat_member_type;
    partner_id = fields.One("res.partner");
    threadAsAgentHistory = fields.One("Thread", {
        compute() {
            if (this.livechat_member_type === "agent") {
                return this.channel_id;
            }
            return false;
        },
    });
    threadAsCustomerHistory = fields.One("Thread", {
        compute() {
            if (this.livechat_member_type === "visitor") {
                return this.channel_id;
            }
            return false;
        },
    });
}
LivechatChannelMemberHistory.register();
