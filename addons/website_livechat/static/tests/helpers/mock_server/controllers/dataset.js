/** @odoo-module **/

import { patch } from "@web/core/utils/patch";
import { MockServer } from "@web/../tests/helpers/mock_server";

patch(MockServer.prototype, 'website_livechat/controllers/dataset', {
    /**
     * @override
     */
     async _performRPC(route, args) {
        if (route === '/web/dataset/call_button') {
            return this._mockCallButton(args);
        }
        return this._super(route, args);
    },
    /**
     * Simulate a 'call_button' operation from a view.
     *
     * @override
     */
    _mockCallButton({ args, kwargs, method, model }) {
        if (model === 'website.visitor' && method === 'action_send_chat_request') {
            return this._mockWebsiteVisitorActionSendChatRequest(args[0]);
        }
        return this._super(...arguments);
    },
});
