/** @odoo-module **/

import { patch } from "@web/core/utils/patch";
import { MockServer } from "@web/../tests/helpers/mock_server";

patch(MockServer.prototype, {
    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * @override
     * @private
     */
    async _performRPC(route, args) {
        if (
            route.indexOf("/documents/image") >= 0 ||
            [".png", ".jpg"].includes(route.substr(route.length - 4))
        ) {
            return Promise.resolve();
        }
        if (args.method === "get_deletion_delay") {
            return 30;
        }
        return super._performRPC(...arguments);
    },
});
