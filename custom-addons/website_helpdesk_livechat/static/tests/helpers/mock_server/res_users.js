/** @odoo-module **/

import '@mail/../tests/helpers/mock_server/models/res_users'; // ensure mail override is applied first.

import { patch } from "@web/core/utils/patch";
import { MockServer } from '@web/../tests/helpers/mock_server';

patch(MockServer.prototype, {
    /**
     * @override
     */
     _mockResUsers_InitMessaging(ids) {
        return Object.assign(
            {},
            super._mockResUsers_InitMessaging(ids),
            {'helpdesk_livechat_active': 1}
        );
    },
});
