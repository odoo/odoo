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
        const responses = this._super(...arguments);
        for (const response of responses) {
            const rating = this._getRecords('rating.rating', [
                ['message_id', '=', response.id],
            ]);
            response.rating_img = "/rating/static/src/img/rating_" + rating[0].rating + ".png";
        }
        return responses;
    },
});
