/** @odoo-module alias=@bus/../tests/helpers/mock_server/models/ir_websocket default=false */

import { patch } from "@web/core/utils/patch";
import { MockServer } from "@web/../tests/helpers/mock_server";

patch(MockServer.prototype, {
    /**
     * Simulates `_build_bus_channel_list` on `ir.websocket`.
     */
    _mockIrWebsocket__buildBusChannelList(channels = []) {
        channels = [...channels];
        channels.push("broadcast");
        const authenticatedUserId = this.pyEnv.cookie.get("authenticated_user_sid");
        const authenticatedPartner = authenticatedUserId
            ? this.pyEnv["res.partner"].search_read([["user_ids", "in", [authenticatedUserId]]], {
                  context: { active_test: false },
              })[0]
            : null;
        if (authenticatedPartner) {
            channels.push(authenticatedPartner);
        }
        return channels;
    },
});
