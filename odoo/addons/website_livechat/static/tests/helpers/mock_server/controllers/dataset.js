/** @odoo-module **/

import { patch } from "@web/core/utils/patch";
import { MockServer } from "@web/../tests/helpers/mock_server";

patch(MockServer.prototype, {
    /**
     * @override
     */
    async _performRPC(route, { args, method, model }) {
        if (
            route === "/web/dataset/call_button" &&
            model === "website.visitor" &&
            method === "action_send_chat_request"
        ) {
            return this._mockWebsiteVisitorActionSendChatRequest(args[0]);
        }
        return super._performRPC(...arguments);
    },
});
