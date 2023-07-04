/** @odoo-module */

import { patch } from "@web/core/utils/patch";
import { MockServer } from "@web/../tests/helpers/mock_server";

patch(MockServer.prototype, {
    async _performRPC(route, args) {
        if (args.method === "get_worklocation") {
            return Promise.resolve()
        }
        return super._performRPC(...arguments);
    },
});