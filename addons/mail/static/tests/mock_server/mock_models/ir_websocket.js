/** @odoo-module */

import { busModels } from "@bus/../tests/bus_test_helpers";
import { isIterable } from "@web/core/utils/arrays";

export class IrWebSocket extends busModels.IrWebSocket {
    /**
     * @override
     * @type {typeof busModels.WebSocket["prototype"]["_getImStatus"]}
     */
    _getImStatus(imStatusIdsByModel) {
        const imStatus = super._getImStatus(imStatusIdsByModel);

        const { "mail.guest": guestIds } = imStatusIdsByModel;
        if (guestIds) {
            imStatus["Persona"] = imStatus["Persona"].concat(
                this.env["mail.guest"]
                    .search_read([["id", "in", guestIds]], {
                        context: { active_test: false },
                        fields: ["im_status"],
                    })
                    .map((g) => ({ ...g, type: "guest" }))
            );
        }

        return imStatus;
    }

    /**
     * @override
     * @type {typeof busModels.WebSocket["prototype"]["_buildBusChannelList"]}
     */
    _buildBusChannelList() {
        const channels = super._buildBusChannelList();

        const guest = this.env["mail.guest"]._getGuestFromContext();
        const authenticatedUserId = this.env.cookie.get("authenticated_user_sid");
        const authenticatedPartner = authenticatedUserId
            ? this.env["res.partner"].search_read([["user_ids", "in", [authenticatedUserId]]], {
                  context: { active_test: false },
              })[0]
            : null;
        if (!authenticatedPartner && !guest) {
            return channels;
        }
        if (guest) {
            channels.push({ model: "mail.guest", id: guest.id });
        }
        const userChannelIds = this.env["discuss.channel.member"]
            .search_read([
                guest ? ["guest_id", "=", guest.id] : ["partner_id", "=", authenticatedPartner.id],
            ])
            .map((member) =>
                isIterable(member.channel_id) ? member.channel_id[0] : member.channel_id
            );
        for (const channelId of userChannelIds) {
            channels.push({ model: "discuss.channel", id: channelId });
        }

        return channels;
    }
}
