/** @odoo-module **/

import { patch } from "@web/core/utils/patch";
import { MockServer } from "@web/../tests/helpers/mock_server";

patch(MockServer.prototype, {
    /**
     * Simulates `_update_presence` on `ir.websocket`.
     *
     * @param inactivityPeriod
     * @param imStatusIdsByModel
     */
    _mockIrWebsocket__updatePresence(inactivityPeriod, imStatusIdsByModel) {
        const imStatusNotifications = this._mockIrWebsocket__getImStatus(imStatusIdsByModel);
        if (Object.keys(imStatusNotifications).length > 0) {
            this._mockBusBus__sendone(
                this.pyEnv.currentPartner,
                "mail.record/insert",
                imStatusNotifications
            );
        }
    },
    /**
     * Simulates `_get_im_status` on `ir.websocket`.
     *
     * @param {Object} imStatusIdsByModel
     * @param {Number[]|undefined} res.partner ids of res.partners whose im_status
     * should be monitored.
     */
    _mockIrWebsocket__getImStatus(imStatusIdsByModel) {
        const imStatus = {};
        const { "res.partner": partnerIds } = imStatusIdsByModel;
        if (partnerIds) {
            imStatus["Persona"] = this.mockSearchRead("res.partner", [[["id", "in", partnerIds]]], {
                context: { active_test: false },
                fields: ["im_status"],
            }).map((p) => ({ ...p, type: "partner" }));
        }
        return imStatus;
    },
    /**
     * Simulates `_build_bus_channel_list` on `ir.websocket`.
     */
    _mockIrWebsocket__buildBusChannelList(channels = []) {
        channels = [...channels];
        channels.push("broadcast");
        const authenticatedUserId = this.pyEnv.cookie.get("authenticated_user_sid");
        const authenticatedPartner = authenticatedUserId
            ? this.pyEnv["res.partner"].searchRead([["user_ids", "in", [authenticatedUserId]]], {
                  context: { active_test: false },
              })[0]
            : null;
        if (authenticatedPartner) {
            channels.push(authenticatedPartner);
        }
        return channels;
    },
});
