/* @odoo-module */

// ensure bus override is applied first.
import "@bus/../tests/helpers/mock_server";

import { patch } from "@web/core/utils/patch";
import { MockServer } from "@web/../tests/helpers/mock_server";

patch(MockServer.prototype, {
    /**
     * Simulates `_get_im_status` on `ir.websocket`.
     *
     * @param {Object} imStatusIdsByModel
     * @param {Number[]|undefined} mail.guest ids of mail.guest whose im_status
     * should be monitored.
     */
    _mockIrWebsocket__getImStatus(imStatusIdsByModel) {
        const imStatus = super._mockIrWebsocket__getImStatus(imStatusIdsByModel);
        const { "mail.guest": guestIds } = imStatusIdsByModel;
        if (guestIds) {
            imStatus["Persona"] = imStatus["Persona"].concat(
                this.pyEnv["mail.guest"]
                    .searchRead([["id", "in", guestIds]], {
                        context: { active_test: false },
                        fields: ["im_status"],
                    })
                    .map((g) => ({ ...g, type: "guest" }))
            );
        }
        return imStatus;
    },
    /**
     * Simulates `_build_bus_channel_list` on `ir.websocket`.
     */
    _mockIrWebsocket__buildBusChannelList() {
        const channels = super._mockIrWebsocket__buildBusChannelList();
        const guest = this._mockMailGuest__getGuestFromContext();
        const authenticatedUserId = this.pyEnv.cookie.get("authenticated_user_sid");
        const authenticatedPartner = authenticatedUserId
            ? this.pyEnv["res.partner"].searchRead([["user_ids", "in", [authenticatedUserId]]], {
                  context: { active_test: false },
              })[0]
            : null;
        if (!authenticatedPartner && !guest) {
            return channels;
        }
        if (guest) {
            channels.push({ model: "mail.guest", id: guest.id });
        }
        const userChannelIds = this.pyEnv["discuss.channel.member"]
            .searchRead([
                guest ? ["guest_id", "=", guest.id] : ["partner_id", "=", authenticatedPartner.id],
            ])
            .map((member) =>
                Array.isArray(member.channel_id) ? member.channel_id[0] : member.channel_id
            );
        for (const channelId of userChannelIds) {
            channels.push({ model: "discuss.channel", id: channelId });
        }
        return channels;
    },
});
