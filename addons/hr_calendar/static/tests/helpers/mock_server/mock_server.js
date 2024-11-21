import { patch } from "@web/core/utils/patch";
import { MockServer } from "@web/../tests/helpers/mock_server";

patch(MockServer.prototype, {
    async _performRPC(route, args) {
        if (args.method === "get_working_hours_for_all_attendees") {
            return [];
        }
        return super._performRPC(route, args);
    },
});
