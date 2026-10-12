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

    _store_member_fields(res) {
        super._store_member_fields(res);
        res.attr("livechat_member_type", undefined, {
            predicate: (m) => {
                const [channel] = this.env["discuss.channel"].browse(m.channel_id);
                return channel?.channel_type === "livechat";
            },
        });
    }

    _store_partner_dynamic_fields(partnerRes) {
        super._store_partner_dynamic_fields(partnerRes);
        const member = this[0];
        const [channel] = this.env["discuss.channel"].browse(member.channel_id);
        if (channel?.channel_type !== "livechat") {
            return;
        }
        partnerRes._fields.length = 0; // mock: mirror partner_res.clear()
        partnerRes.attr("active");
        partnerRes.one("country_id", ["code", "name"]);
        partnerRes.attr("is_public");
        partnerRes.from_method("_store_avatar_fields");
        partnerRes.from_method("_store_livechat_username_fields");
        partnerRes.from_method("_store_mention_fields");
        if (member.livechat_member_type === "visitor") {
            partnerRes.attr("email");
            partnerRes.many("user_ids", ["offline_since"]);
        }
        partnerRes.from_method("_store_im_status_fields", { internal: true });
    }

    _store_guest_dynamic_fields(guestRes) {
        super._store_guest_dynamic_fields(guestRes);
        const member = this[0];
        const [channel] = this.env["discuss.channel"].browse(member.channel_id);
        if (channel?.channel_type !== "livechat") {
            return;
        }
        guestRes._fields.length = 0; // mock: mirror guest_res.clear()
        guestRes.one("country_id", ["code", "name"]);
        guestRes.attr("offline_since");
        guestRes.from_method("_store_avatar_fields");
        guestRes.from_method("_store_im_status_fields", { internal: true });
    }
}
