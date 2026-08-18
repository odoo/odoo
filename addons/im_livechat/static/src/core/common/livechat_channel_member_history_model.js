import { fields, Record } from "@mail/model/export";

export class LivechatChannelMemberHistory extends Record {
    static _name = "im_livechat.channel.member.history";

    setup() {
        super.setup();
        this.assignComputed("channelAsAgentHistory", function computeChannelAsAgentHistory() {
            return this.livechat_member_type === "agent" ? this.channel_id : false;
        });
        this.assignComputed("channelAsBotHistory", function computeChannelAsBotHistory() {
            return this.livechat_member_type === "bot" ? this.channel_id : false;
        });
        this.assignComputed("channelAsCustomerHistory", function computeChannelAsCustomerHistory() {
            return this.livechat_member_type === "visitor" ? this.channel_id : false;
        });
    }

    channel_id = fields.One("discuss.channel", { inverse: "livechat_channel_member_history_ids" });
    channelAsAgentHistory = fields.One("discuss.channel", {
        inverse: "livechat_agent_history_ids",
    });
    channelAsBotHistory = fields.One("discuss.channel", {
        inverse: "livechat_bot_history_ids",
    });
    channelAsCustomerHistory = fields.One("discuss.channel", {
        inverse: "livechat_customer_history_ids",
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
