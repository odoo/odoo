import { mailModels } from "@mail/../tests/mail_test_helpers";

export class DiscussChannelMember extends mailModels.DiscussChannelMember {
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
            return ["active", "country", "is_public", "user_livechat_username", "write_date"];
        }
        return super._get_store_partner_fields(...arguments);
    }
}
