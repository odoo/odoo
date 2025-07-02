import { mailModels } from "@mail/../tests/mail_test_helpers";
import { fields } from "@web/../tests/web_test_helpers";

export class DiscussChannelMember extends mailModels.DiscussChannelMember {
    livechat_member_type = fields.Selection({
        selection: [
            ["agent", "Agent"],
            ["visitor", "Visitor"],
            ["bot", "Chatbot"],
        ],
        compute: false,
    });
    /**
     * @override
     * @type {typeof mailModels.DiscussChannelMember["prototype"]["_get_store_partner_fields"]}
     */
    _get_store_partner_fields(ids, fields) {
        /** @type {import("mock_models").DiscussChannel} */
        const DiscussChannel = this.env["discuss.channel"];

        const [member] = this.browse(ids);
        const [channel] = DiscussChannel.browse(member.channel_id);
        if (channel.channel_type === "livechat") {
            const fields = [
                "active",
                "avatar_128",
                "country_id",
                "is_public",
                "user_livechat_username",
            ];
            if (this.livechat_member_type == "visitor") {
                fields.push("offline_since", "email");
            }
        }
        return super._get_store_partner_fields(...arguments);
    }
    /**
     * @override
     * @type {typeof mailModels.DiscussChannelMember["prototype"]["_to_store"]}
     */
    _to_store(ids, store, fields, extra_fields) {
        super._to_store(...arguments);
        const members = this.browse(ids);
        for (const member of members) {
            store.add(this.browse(member.id), {
                livechat_member_type: member.livechat_member_type,
            });
        }
    }
}
