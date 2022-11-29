/** @odoo-module **/

import { registry } from "@web/core/registry";
import { patch } from "@web/core/utils/patch";
import { MockServer } from "@web/../tests/helpers/mock_server";

patch(MockServer.prototype, "mail/mock_server_main", {
    async performRPC(route, args) {
        const rpcResult = await this._super(route, args);
        const methodName = args.method || route;
        const callbackFn =
            registry.category("mock_server_callbacks").get(`${args.model}/${methodName}`, null) ||
            registry.category("mock_server_callbacks").get(methodName, null);
        if (callbackFn) {
            callbackFn(args);
        }
        return rpcResult;
    },
});
