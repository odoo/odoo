import { patch } from "@web/core/utils/patch";
import { MockServer } from "@web/../tests/helpers/mock_server";

patch(MockServer.prototype, {
    async _performRPC(_route, { model, method, args }) {
        if (model === "res.company" && method === "read") {
            return [];
        }
        return super._performRPC(...arguments);
    },
});
