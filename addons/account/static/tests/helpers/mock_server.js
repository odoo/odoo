import { patch } from "@web/core/utils/patch";
import { MockServer } from "@web/../tests/helpers/mock_server";

patch(MockServer.prototype, {
    async _performRPC(_route, { model, method, args }) {
        if (model === "account.move" && method === "get_extra_print_items") {
            return [];
        }
        return super._performRPC(...arguments);
    },
});
