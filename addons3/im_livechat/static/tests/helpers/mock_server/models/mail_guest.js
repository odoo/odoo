/* @odoo-module */

import { patch } from "@web/core/utils/patch";
import { MockServer } from "@web/../tests/helpers/mock_server";

patch(MockServer.prototype, {
    /**
     * Simulates `_set_auth_cookie` on `mail.guest`.
     */
    _mockMailGuest__setAuthCookie(guestId) {
        this.pyEnv.cookie.set("dgid", guestId);
    },
});
