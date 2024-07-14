/** @odoo-module **/

import '@mail/../tests/helpers/mock_server/models/res_users'; // ensure mail overrides are applied first
import { patch } from "@web/core/utils/patch";
import { MockServer } from "@web/../tests/helpers/mock_server";

patch(MockServer.prototype, {
    /**
     * @override
     * @returns {Object}
     */
    _mockResUsers_InitMessaging(...args) {
        return {
            ...super._mockResUsers_InitMessaging(...args),
            'hasDocumentsUserGroup': true,
        };
    },
});
