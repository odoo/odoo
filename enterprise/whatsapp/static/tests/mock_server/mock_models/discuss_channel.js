import { mailModels } from "@mail/../tests/mail_test_helpers";
import { mailDataHelpers } from "@mail/../tests/mock_server/mail_mock_server";

import { fields, makeKwArgs, serverState } from "@web/../tests/web_test_helpers";
import { serializeDateTime } from "@web/core/l10n/dates";

const { DateTime } = luxon;

export class DiscussChannel extends mailModels.DiscussChannel {
    whatsapp_channel_valid_until = fields.Datetime({
        default: () => serializeDateTime(DateTime.local().plus({ days: 1 })),
    });

    /**
     * @override
     * @type {typeof mailModels.DiscussChannel["prototype"]["_to_store"]}
     */
    _to_store(ids, store) {
        /** @type {import("mock_models").ResPartner} */
        const ResPartner = this.env["res.partner"];

        super._to_store(...arguments);
        const channels = this._filter([
            ["id", "in", ids],
            ["channel_type", "=", "whatsapp"],
        ]);
        for (const channel of channels) {
            store.add(this.browse(channel.id), {
                whatsapp_channel_valid_until: channel.whatsapp_channel_valid_until || false,
                whatsapp_partner_id: mailDataHelpers.Store.one(
                    ResPartner.browse(channel.whatsapp_partner_id),
                    makeKwArgs({ only_id: true })
                ),
            });
        }
    }

    /** @param {number[]} ids */
    whatsapp_channel_join_and_pin(ids) {
        /** @type {import("mock_models").DiscussChannel} */
        const DiscussChannel = this.env["discuss.channel"];
        /** @type {import("mock_models").DiscussChannelMember} */
        const DiscussChannelMember = this.env["discuss.channel.member"];
        /** @type {import("mock_models").BusBus} */
        const BusBus = this.env["bus.bus"];
        const [channel] = this.browse(ids);

        const selfMember = this._find_or_create_member_for_self(channel.id);
        if (selfMember) {
            DiscussChannelMember.write([selfMember.id], {
                unpin_dt: false,
            });
        } else {
            const selfMemberId = DiscussChannelMember.create({
                channel_id: channel.id,
                partner_id: serverState.partnerId,
                create_uid: this.env.uid,
            });
            this.message_post(
                channel.id,
                makeKwArgs({
                    body: "<div class='o_mail_notification'>joined the channel</div>",
                    message_type: "notification",
                    subtype_xmlid: "mail.mt_comment",
                })
            );
            const broadcast_store = new mailDataHelpers.Store(this.browse(channel.id), {
                memberCount: DiscussChannelMember.search_count([["channel_id", "=", channel.id]]),
            });
            broadcast_store.add(DiscussChannelMember.browse(selfMemberId));
            BusBus._sendone(channel, "mail.record/insert", broadcast_store.get_result());
        }
        return new mailDataHelpers.Store(DiscussChannel.browse(channel.id)).get_result();
    }
    /**
     * @override
     * @type {typeof mailModels.DiscussChannel["prototype"]["_types_allowing_seen_infos"]}
     */
    _types_allowing_seen_infos() {
        return super._types_allowing_seen_infos(...arguments).concat(["whatsapp"]);
    }
}
