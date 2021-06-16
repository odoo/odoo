/** @odoo-module **/

import '@mail/../tests/helpers/mock_server'; // ensure mail overrides are applied first

import MockServer from 'web.MockServer';

MockServer.include({
    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * @override
     */

    //--------------------------------------------------------------------------
    // Private Mocked Routes
    //--------------------------------------------------------------------------

    /**
     * Simulates `message_format` on `mail.message`.
     *
     * @private
     * @override
     * @returns {integer[]} ids
     * @returns {Object[]}
     */
     _mockMailMessageMessageFormat(ids) {
        const messageFormat = this._super(...arguments);
        for (const formatter of messageFormat) {
            const rating = this._getRecords('rating.rating', [
                ['message_id', '=', formatter.id],
            ]);
            if (rating.length > 0) {
                formatter.rating_val = rating[0].rating;
            }
        }
        return messageFormat;
    },
});
