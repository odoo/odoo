/** @odoo-module **/

import { patch } from "@web/core/utils/patch";
import { MockServer } from "@web/../tests/helpers/mock_server";

patch(MockServer.prototype, {
    /**
     * @override
     */
    async _performRPC(route, args) {
        if (args.method === "gantt_resource_employees_working_periods") {
            return { working_periods: {} };
        }
        return super._performRPC(...arguments);
    },
});
