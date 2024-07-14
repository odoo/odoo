/* @odoo-module */

import "@mail/../tests/helpers/mock_server/models/res_users"; // ensure mail overrides are applied first

import { patch } from "@web/core/utils/patch";
import { MockServer } from "@web/../tests/helpers/mock_server";

patch(MockServer.prototype, {
    /**
     * @override
     */
    _mockResUsers_InitMessaging(...args) {
        const getConfig = (key) =>
            this.getRecords("ir.config_parameter", [["key", "=", key]])[0].value;
        return {
            ...super._mockResUsers_InitMessaging(...args),
            voipConfig: {
                mode: getConfig("voip.mode"),
                pbxAddress: getConfig("voip.pbx_ip"),
                webSocketUrl: getConfig("voip.wsServer"),
            },
        };
    },
});
