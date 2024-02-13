/** @odoo-module **/

import { constants, models } from "@web/../tests/web_test_helpers";

export class IrWebSocket extends models.ServerModel {
    _name = "ir.websocket";

    /**
     * @param {number} inactivityPeriod
     * @param {number[]} imStatusIdsByModel
     */
    _update_presence(inactivityPeriod, imStatusIdsByModel) {
        const imStatusNotifications = this._get_im_status(imStatusIdsByModel);
        if (Object.keys(imStatusNotifications).length > 0) {
            const [partner] = this.env["res.partner"].read(constants.PARTNER_ID);
            this.env["bus.bus"]._sendone(partner, "mail.record/insert", imStatusNotifications);
        }
    }

    /** @param {Record<string, number[]>} imStatusIdsByModel */
    _get_im_status({ "res.partner": partnerIds }) {
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
     * @returns {string[]}
     */
    _build_bus_channel_list() {
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
