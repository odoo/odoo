import { fields, models } from "@web/../tests/web_test_helpers";

export class LivechatChannelMemberHistory extends models.ServerModel {
    _name = "im_livechat.channel.member.history";

    channel_id = fields.Many2one({ relation: "discuss.channel" });
    guest_id = fields.Many2one({
        relation: "mail.guest",
    });
    livechat_member_type = fields.Selection({
        selection: [
            ["agent", "Agent"],
            ["visitor", "Visitor"],
            ["bot", "Chatbot"],
        ],
    });
    member_id = fields.Many2one({ relation: "discuss.channel.member" });
    partner_id = fields.Many2one({ relation: "res.partner" });
}
