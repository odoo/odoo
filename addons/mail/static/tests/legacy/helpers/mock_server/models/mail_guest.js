/** @odoo-module alias=@mail/../tests/helpers/mock_server/models/mail_guest default=false */

import { patch } from "@web/core/utils/patch";
import { MockServer } from "@web/../tests/helpers/mock_server";

patch(MockServer.prototype, {
    _mockMailGuest__getGuestFromContext() {
        const guestId = this.pyEnv?.cookie.get("dgid");
        return guestId ? this.pyEnv["mail.guest"].search_read([["id", "=", guestId]])[0] : null;
    },
});
