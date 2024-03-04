import { busModels } from "@bus/../tests/bus_test_helpers";
import { isIterable } from "@web/core/utils/arrays";

export class IrWebSocket extends busModels.IrWebSocket {
    /**
     * @override
     * @type {typeof busModels.WebSocket["prototype"]["_get_im_status"]}
     */
    _get_im_status(imStatusIdsByModel) {
        /** @type {import("mock_models").MailGuest} */
        const MailGuest = this.env["mail.guest"];

        const imStatus = super._get_im_status(imStatusIdsByModel);
        const { "mail.guest": guestIds } = imStatusIdsByModel;
        if (guestIds) {
            imStatus["Persona"] = imStatus["Persona"].concat(
                MailGuest.search_read([["id", "in", guestIds]], {
                    context: { active_test: false },
                    fields: ["im_status"],
                }).map((g) => ({ ...g, type: "guest" }))
            );
        }
        return imStatus;
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
            ? ResPartner.search_read([["user_ids", "in", [authenticatedUserId]]], {
                  context: { active_test: false },
              })
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
}
