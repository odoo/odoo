/** @odoo-module **/

import '@mail/../tests/helpers/mock_server'; // ensure mail overrides are applied first

import { patch } from "@web/core/utils/patch";
import { MockServer } from "@web/../tests/helpers/mock_server";

patch(MockServer.prototype, 'snailmail', {
    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * @override
     */
    async performRPC(route, args) {
        if (args.model === 'mail.message' && args.method === 'cancel_letter') {
            const ids = args.args[0];
            return this._mockMailMessageCancelLetter(ids);
        }
        if (args.model === 'mail.message' && args.method === 'send_letter') {
            const ids = args.args[0];
            return this._mockMailMessageSendLetter(ids);
        }
        if (args.method === 'get_credits_url') {
            // random value returned in order for the mock server to know that this route is implemented.
            return true;
        }
        return this._super(...arguments);
    },

    //--------------------------------------------------------------------------
    // Private Mocked Methods
    //--------------------------------------------------------------------------

    /**
     * Simulates `cancel_letter` on `mail.message`.
     *
     * @private
     * @param {integer[]} ids
     */
    _mockMailMessageCancelLetter(ids) {
        // TODO implement this mock and improve related tests (task-2300496)
        // random value returned in order for the mock server to know that this route is implemented.
        return true;
    },
    /**
     * Simulates `send_letter` on `mail.message`.
     *
     * @private
     * @param {integer[]} ids
     */
    _mockMailMessageSendLetter(ids) {
        // TODO implement this mock and improve related tests (task-2300496)
        // random value returned in order for the mock server to know that this route is implemented.
        return true;
    },
});
