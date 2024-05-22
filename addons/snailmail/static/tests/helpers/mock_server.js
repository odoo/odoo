odoo.define('snailmail/static/tests/helpers/mock_server.js', function (require) {
"use strict";

const MockServer = require('web.MockServer');

MockServer.include({
    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * @override
     */
    async _performRpc(route, args) {
        if (args.model === 'mail.message' && args.method === 'cancel_letter') {
            const ids = args.args[0];
            return this._mockMailMessageCancelLetter(ids);
        }
        if (args.model === 'mail.message' && args.method === 'send_letter') {
            const ids = args.args[0];
            return this._mockMailMessageSendLetter(ids);
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
    },
    /**
     * Simulates `send_letter` on `mail.message`.
     *
     * @private
     * @param {integer[]} ids
     */
    _mockMailMessageSendLetter(ids) {
        // TODO implement this mock and improve related tests (task-2300496)
    },
});

});
