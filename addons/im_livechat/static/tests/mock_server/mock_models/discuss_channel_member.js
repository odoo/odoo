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
    _get_store_partner_fields(fields) {
        /** @type {import("mock_models").DiscussChannel} */
        const DiscussChannel = this.env["discuss.channel"];

        const member = this[0];
        const [channel] = DiscussChannel.browse(member.channel_id);
        if (channel.channel_type === "livechat") {
            if (!fields) {
                fields = [
                    "active",
                    "avatar_128",
                    "country_id",
                    "im_status",
                    "is_public",
                    "user_livechat_username",
                ];
                if (member.livechat_member_type == "visitor") {
                    fields.push("offline_since", "email");
                }
            }
        }
        return super._get_store_partner_fields(fields);
    }
    /**
     * @override
     * @type {typeof mailModels.DiscussChannelMember["prototype"]["_to_store"]}
     */
    _to_store(store, fields, extra_fields) {
        super._to_store(...arguments);
        for (const member of this) {
            store._add_record_fields(this.browse(member.id), {
                livechat_member_type: member.livechat_member_type,
            });
        }
    }
}
