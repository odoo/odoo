odoo.define('google_drive.MockServer', function (require) {
    'use strict';

    var MockServer = require('web.MockServer');

    MockServer.include({
        //--------------------------------------------------------------------------
        // Private
        //--------------------------------------------------------------------------

        /**
         * @override
         * @private
         */
        async _performRpc(route, args) {
            if (args.method === 'get_google_drive_config') {
                return [];
            }
            return this._super(...arguments);
        },
    });
});
