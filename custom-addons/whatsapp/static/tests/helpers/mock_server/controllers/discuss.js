/* @odoo-module */

import { patch } from "@web/core/utils/patch";
import { MockServer } from "@web/../tests/helpers/mock_server";

patch(MockServer.prototype, {
    async _mockRouteMailThreadData(thread_model, thread_id, request_list) {
        const res = await super._mockRouteMailThreadData(thread_model, thread_id, request_list);
        res.canSendWhatsapp =
            this.pyEnv["whatsapp.template"].searchCount([
                ["model", "=", thread_model],
                ["status", "=", "approved"],
            ]) > 0;
        return res;
    },
});
