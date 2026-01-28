import { fields, Record } from "@mail/model/export";

export class LivechatChannelMemberHistory extends Record {
    static _name = "im_livechat.channel.member.history";

    channel_id = fields.One("discuss.channel", { inverse: "livechat_channel_member_history_ids" });
    channelAsAgentHistory = fields.One("discuss.channel", {
        inverse: "livechat_agent_history_ids",
        compute() {
            if (this.livechat_member_type === "agent") {
                return this.channel_id;
            }
            return false;
        },
    });
    channelAsCustomerHistory = fields.One("discuss.channel", {
        inverse: "livechat_customer_history_ids",
        compute() {
            if (this.livechat_member_type === "visitor") {
                return this.channel_id;
            }
            return false;
        },
    });
    member_id = fields.One("discuss.channel.member");
    guest_id = fields.One("mail.guest");
    /** @type {number} */
    id;
    /** @type {"agent"|"visitor"|"bot"} */
    livechat_member_type;
    partner_id = fields.One("res.partner");
}
LivechatChannelMemberHistory.register();
