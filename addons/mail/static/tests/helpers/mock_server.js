odoo.define('mail.MockServer', function (require) {
"use strict";

var MockServer = require('web.MockServer');

MockServer.include({
    /**
     * @override
     */
    _performRpc: function (route, args) {
        if (route === '/mail/init_messaging') {
            return $.when(this._mockInitMessaging(args));
        }
        return this._super(route, args);
    },
    /**
     * Simulate the '/mail/init_messaging' route
     *
     * @private
     * @return {Object}
     */
    _mockInitMessaging: function () {
        return {
            'needaction_inbox_counter': 0,
            'starred_counter': 0,
            'channel_slots': [],
            'commands': [],
            'mention_partner_suggestions': [],
            'shortcodes': [],
            'menu_id': false,
        };
    },
});

});
