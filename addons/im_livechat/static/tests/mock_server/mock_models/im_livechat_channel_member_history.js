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

    _store_member_history_fields(res) {
        res.attr("channel_id");
        res.one("guest_id", ["name"], { predicate: (r) => !r.partner_id });
        res.attr("livechat_member_type");
        res.attr("member_id");
        // sudo: res.partner - reading partner of an accessible channel member history is acceptable
        res.one("partner_id", "_store_livechat_member_fields", {
            predicate: (r) => !r.guest_id,
            sudo: true,
        });
    }

    create(values) {
        const idOrIds = super.create(values);
        // Update of the livechat_channel_member_history_ids field in discuss.channel
        // since it is not done automatically for the mock server models.
        const channel_member_history =
            this.env["im_livechat.channel.member.history"].browse(idOrIds);
        channel_member_history.forEach((history) => {
            const channelId = this.env["discuss.channel"].browse(history.channel_id)[0];
            channelId.livechat_channel_member_history_ids = [
                ...(channelId.livechat_channel_member_history_ids || []),
                history.id,
            ];
        });
        return idOrIds;
    }
}
