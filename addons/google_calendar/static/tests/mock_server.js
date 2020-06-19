odoo.define('google_calendar.MockServer', function (require) {
    'use strict';

    var MockServer = require('web.MockServer');

    MockServer.include({
        /**
         * @override
         * @private
         * @returns {Promise}
         */
        _performRpc(route, args) {
            if (route === '/google_calendar/sync_data') {
                return Promise.resolve({status: 'no_new_event_from_google'});
            } else {
                return this._super(...arguments);
            }
        },
    });
});
