/** @odoo-module **/

import { models } from "@web/../tests/web_test_helpers";

export class IrWebSocket extends models.ServerModel {
    _name = "ir.websocket";

    /**
     * @param {number} inactivityPeriod
     * @param {number[]} imStatusIdsByModel
     */
    _update_presence(inactivityPeriod, imStatusIdsByModel) {
        /** @type {import("mock_models").BusBus} */
        const BusBus = this.env["bus.bus"];
        /** @type {import("mock_models").ResPartner} */
        const ResPartner = this.env["res.partner"];

        const imStatusNotifications = this._get_im_status(imStatusIdsByModel);
        if (Object.keys(imStatusNotifications).length > 0) {
            if (this.env.user) {
                const [partner] = ResPartner.read(this.env.user.partner_id);
                BusBus._sendone(partner, "mail.record/insert", imStatusNotifications);
            }
        }
    }

    /** @param {Record<string, number[]>} imStatusIdsByModel */
    _get_im_status({ "res.partner": partnerIds }) {
        const imStatus = {};
        if (partnerIds) {
            imStatus["Persona"] = this.env["res.partner"]
                .search_read([["id", "in", partnerIds]], ["im_status"])
                .map((p) => ({ ...p, type: "partner" }));
        }
        return imStatus;
    }

    /**
     * @returns {string[]}
     */
    _build_bus_channel_list(channels = []) {
        /** @type {import("mock_models").ResPartner} */
        const ResPartner = this.env["res.partner"];

        channels = [...channels];
        channels.push("broadcast");
        const authenticatedUserId = this.env.cookie.get("authenticated_user_sid");
        const [authenticatedPartner] = authenticatedUserId
            ? ResPartner.search_read([["user_ids", "in", [authenticatedUserId]]], {
                  context: { active_test: false },
              })
            : [];
        if (authenticatedPartner) {
            channels.push(authenticatedPartner);
        }
        return channels;
    }
}
