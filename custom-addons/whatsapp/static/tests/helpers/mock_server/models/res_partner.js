/* @odoo-module */

import "@mail/../tests/helpers/mock_server/models/res_partner"; // ensure mail overrides are applied first

import { patch } from "@web/core/utils/patch";
import { MockServer } from "@web/../tests/helpers/mock_server";

patch(MockServer.prototype, {
    /**
     * @override
     */
    _mockResPartner_GetChannelsAsMember(ids) {
        const partner = this.getRecords("res.partner", [["id", "in", ids]])[0];
        const members = this.getRecords("discuss.channel.member", [
            ["partner_id", "=", partner.id],
            ["is_pinned", "=", true],
        ]);
        const whatsappChannels = this.getRecords("discuss.channel", [
            ["channel_type", "=", "whatsapp"],
            ["channel_member_ids", "in", members.map((member) => member.id)],
        ]);
        return [...super._mockResPartner_GetChannelsAsMember(ids), ...whatsappChannels];
    },
});
