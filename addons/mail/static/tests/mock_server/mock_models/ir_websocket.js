import { busModels } from "@bus/../tests/bus_test_helpers";

import { mailDataHelpers } from "@mail/../tests/mock_server/mail_mock_server";

import { makeKwArgs } from "@web/../tests/web_test_helpers";
import { isIterable } from "@web/core/utils/arrays";

export class IrWebSocket extends busModels.IrWebSocket {
    /**
     * @override
     * @type {typeof busModels.WebSocket["prototype"]["_get_im_status"]}
     */
    _im_status_to_store(store, imStatusIdsByModel) {
        /** @type {import("mock_models").MailGuest} */
        const MailGuest = this.env["mail.guest"];
        /** @type {import("mock_models").ResPartner} */
        const ResPartner = this.env["res.partner"];

        const { "mail.guest": guestIds, "res.partner": partnerIds } = imStatusIdsByModel;
        if (guestIds) {
            store.add(
                "mail.guest",
                MailGuest.browse(guestIds).map((guest) => ({
                    id: guest.id,
                    im_status: guest.im_status,
                }))
            );
        }
        if (partnerIds) {
            store.add(
                "res.partner",
                ResPartner.browse(partnerIds).map((partner) => ({
                    id: partner.id,
                    im_status: partner.im_status,
                }))
            );
        }
    }

    /**
     * @override
     * @type {typeof busModels.IrWebSocket["prototype"]["_build_bus_channel_list"]}
     */
    _build_bus_channel_list(channels) {
        /** @type {import("mock_models").DiscussChannel} */
        const DiscussChannel = this.env["discuss.channel"];
        /** @type {import("mock_models").DiscussChannelMember} */
        const DiscussChannelMember = this.env["discuss.channel.member"];
        /** @type {import("mock_models").MailGuest} */
        const MailGuest = this.env["mail.guest"];
        /** @type {import("mock_models").ResPartner} */
        const ResPartner = this.env["res.partner"];

        channels = [...super._build_bus_channel_list(channels)];
        const guest = MailGuest._get_guest_from_context();
        const authenticatedUserId = this.env.cookie.get("authenticated_user_sid");
        const [authenticatedPartner] = authenticatedUserId
            ? ResPartner.search_read(
                  [["user_ids", "in", [authenticatedUserId]]],
                  makeKwArgs({ context: { active_test: false } })
              )
            : [];
        if (!authenticatedPartner && !guest) {
            return channels;
        }
        if (guest) {
            channels.push({ model: "mail.guest", id: guest.id });
        }
        const discussChannelIds = channels
            .filter((c) => typeof c === "string" && c.startsWith("discuss.channel_"))
            .map((c) => Number(c.split("_")[1]));

        channels = channels.filter(
            (c) => typeof c !== "string" || !c.startsWith("discuss.channel_")
        );
        const allChannels = DiscussChannel.search_read([
            [
                "id",
                "in",
                DiscussChannelMember.search_read([
                    "|",
                    guest
                        ? ["guest_id", "=", guest.id]
                        : ["partner_id", "=", authenticatedPartner.id],
                    ["channel_id", "in", discussChannelIds],
                ]).map((member) =>
                    isIterable(member.channel_id) ? member.channel_id[0] : member.channel_id
                ),
            ],
        ]);
        for (const channel of allChannels) {
            channels.push(channel);
            if (!discussChannelIds.includes(channel.id)) {
                channels.push([channel, "members"]);
            }
        }
        return channels;
    }
    /**
     * @param {number} inactivityPeriod
     * @param {number[]} imStatusIdsByModel
     */
    _update_presence(inactivityPeriod, imStatusIdsByModel) {
        super._update_presence(inactivityPeriod, imStatusIdsByModel);

        /** @type {import("mock_models").BusBus} */
        const BusBus = this.env["bus.bus"];
        /** @type {import("mock_models").ResPartner} */
        const ResPartner = this.env["res.partner"];

        const store = new mailDataHelpers.Store();
        this._im_status_to_store(store, imStatusIdsByModel);
        if (Object.keys(store.get_result()).length > 0) {
            if (this.env.user) {
                const [partner] = ResPartner.read(this.env.user.partner_id);
                BusBus._sendone(partner, "mail.record/insert", store.get_result());
            }
        }
    }
}
