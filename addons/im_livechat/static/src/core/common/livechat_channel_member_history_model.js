import { fields, Record } from "@mail/model/export";

export class LivechatChannelMemberHistory extends Record {
    static _name = "im_livechat.channel.member.history";

    setup() {
        super.setup(...arguments);
        this.onChange(
            () => {
                const channel = this.channel_id ?? false;
                return [
                    this.livechat_member_type === "agent" ? channel : false,
                    this.livechat_member_type === "bot" ? channel : false,
                    this.livechat_member_type === "visitor" ? channel : false,
                ];
            },
            function onChangeHistoryChannels(agentChannel, botChannel, customerChannel) {
                this.channelAsAgentHistory = agentChannel;
                this.channelAsBotHistory = botChannel;
                this.channelAsCustomerHistory = customerChannel;
            },
            { immediate: true }
        );
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
