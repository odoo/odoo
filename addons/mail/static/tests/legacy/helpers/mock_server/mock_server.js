/** @odoo-module alias=@mail/../tests/helpers/mock_server/mock_server default=false */

import { registry } from "@web/core/registry";
import { patch } from "@web/core/utils/patch";
import { MockServer } from "@web/../tests/helpers/mock_server";

patch(MockServer.prototype, {
    async performRPC(route, args) {
        const rpcResult = await super.performRPC(route, args);
        const methodName = args.method || route;
        const callbackFn =
            registry.category("mock_server_callbacks").get(`${args.model}/${methodName}`, null) ||
            registry.category("mock_server_callbacks").get(methodName, null);
        if (callbackFn) {
            callbackFn(args);
        }
        return rpcResult;
    },

    mockGetViews(modelName, kwargs) {
        const result = super.mockGetViews(...arguments);
        for (const modelName of Object.keys(result.models)) {
            if (this.models[modelName].has_activities) {
                result.models[modelName].has_activities = true;
            }
        }
        return result;
    },
});
