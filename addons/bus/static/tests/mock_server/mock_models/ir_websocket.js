/** @odoo-module **/

import { models } from "@web/../tests/web_test_helpers";

export class IrWebSocket extends models.ServerModel {
    _name = "ir.websocket";

    /**
     * Simulates `_update_presence` on `ir.websocket`.
     *
     * @param {number} inactivityPeriod
     * @param {number[]} imStatusIdsByModel
     */
    _updatePresence(inactivityPeriod, imStatusIdsByModel) {
        const imStatusNotifications = this._getImStatus(imStatusIdsByModel);
        if (Object.keys(imStatusNotifications).length > 0) {
            this.env["bus.bus"]._sendone(
                this.env.partner,
                "mail.record/insert",
                imStatusNotifications
            );
        }
    }

    /**
     * Simulates `_get_im_status` on `ir.websocket`.
     *
     * @param {Record<string, number[]>} imStatusIdsByModel
     */
    _getImStatus({ "res.partner": partnerIds }) {
        const imStatus = {};
        if (partnerIds) {
            imStatus["Persona"] = this.env["res.partner"]
                .search_read([["id", "in", partnerIds]], ["im_status"], {
                    context: { active_test: false },
                })
                .map((p) => ({ ...p, type: "partner" }));
        }
        return imStatus;
    }

    /**
     * Simulates `_build_bus_channel_list` on `ir.websocket`.
     *
     * @returns {string[]}
     */
    _buildBusChannelList() {
        const channels = ["broadcast"];
        const authenticatedUserId = this.env.cookie.get("authenticated_user_sid");
        const authenticatedPartner = authenticatedUserId
            ? this.env["res.partner"].searchRead([["user_ids", "in", [authenticatedUserId]]], {
                  context: { active_test: false },
              })[0]
            : null;
        if (authenticatedPartner) {
            channels.push({ model: "res.partner", id: authenticatedPartner.id });
        }
        return channels;
    }
}
