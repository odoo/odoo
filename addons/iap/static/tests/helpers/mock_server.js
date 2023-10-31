odoo.define('iap/static/tests/helpers/mock_server.js', function (require) {
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
        if (args.model === 'iap.account' && args.method === 'get_credits_url') {
            const service_name = args.args[0] || args.kwargs.service_name;
            const base_url = args.args[1] || args.kwargs.base_url;
            const credit = args.args[2] !== undefined ? args.args[2] : args.kwargs.credit;
            const trial = args.args[3] !== undefined ? args.args[3] : args.kwargs.trial;
            return this._mockIapAccountGetCreditsUrl(service_name, base_url, credit, trial);
        }
        return this._super(...arguments);
    },

    //--------------------------------------------------------------------------
    // Private Mocked Routes
    //--------------------------------------------------------------------------

    /**
     * Simulates `get_credits_url` on `iap.account`.
     *
     * @private
     * @param {string} service_name
     * @param {string} [base_url='']
     * @param {number} [credit=0]
     * @param {boolean} [trial=false]
     * @returns {string}
     */
    _mockIapAccountGetCreditsUrl(service_name, base_url = '', credit = 0, trial = false) {
        // This mock could be improved, in particular by returning an URL that
        // is actually mocked here and including all params, but it is not done
        // due to URL not being used in any test at the time of this comment.
        return base_url + '/random/url?service_name=' + service_name;
    },
});

});
