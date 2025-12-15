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

    create(values) {
        const idOrIds = super.create(values);
        const newMembers = this.browse(idOrIds);
        const historyValues = newMembers.map((member) => ({
            member_id: member.id,
            channel_id: member.channel_id,
            guest_id: member.guest_id,
            partner_id: member.partner_id,
            livechat_member_type: member.livechat_member_type,
        }));
        this.env["im_livechat.channel.member.history"].create(historyValues);
        const guest = this.env["mail.guest"]._get_guest_from_context();
        for (const member of newMembers.filter((m) => {
            const [channel] = this.env["discuss.channel"].browse(m.channel_id);
            return channel.channel_type === "livechat" && !m.livechat_member_type;
        })) {
            if (guest && member.is_self) {
                const livechatCustomerGuestIds = this.env["im_livechat.channel.member.history"]
                    .search_read([
                        ["channel_id", "=", member.channel_id],
                        ["guest_id", "=", guest.id],
                    ])
                    .map(({ guest_id }) => guest_id[0]);
                if (livechatCustomerGuestIds.includes(guest.id)) {
                    member.livechat_member_type = "visitor";
                }
            } else {
                member.livechat_member_type = "agent";
            }
        }
        return idOrIds;
    }

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
    get _to_store_defaults() {
        return super._to_store_defaults.concat(["livechat_member_type"]);
    }
}
