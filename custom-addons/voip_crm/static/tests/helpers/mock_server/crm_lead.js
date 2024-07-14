/* @odoo-module */

import { patch } from "@web/core/utils/patch";
import { MockServer } from "@web/../tests/helpers/mock_server";

patch(MockServer.prototype, {
    /**
     * @override
     */
    async _performRPC(_route, { model, method, args, kwargs }) {
        if (model !== "crm.lead") {
            return super._performRPC(...arguments);
        }
        switch (method) {
            case "get_formview_id":
                return this._mockCrmLeadGetFormviewId(...args, kwargs);
            default:
                return super._performRPC(...arguments);
        }
    },
    _mockCrmLeadGetFormviewId() {
        return false;
    },
});
