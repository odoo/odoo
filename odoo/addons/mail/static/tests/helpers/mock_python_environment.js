/* @odoo-module */

import { pyEnvTarget } from "@bus/../tests/helpers/mock_python_environment";

import { patch } from "@web/core/utils/patch";

patch(pyEnvTarget, {
    async withGuest(guestId, fn) {
        const [guest] = await this.mockServer.getRecords("mail.guest", [["id", "=", guestId]]);
        const originalGuest = this.cookie.get("dgid");
        if (!guest) {
            throw new Error(`Guest ${guestId} not found`);
        }
        let result;
        try {
            this.cookie.set("dgid", guestId);
            result = await this.withUser(this.publicUserId, fn);
        } finally {
            this.cookie.set("dgid", originalGuest);
        }
        return result;
    },
});
