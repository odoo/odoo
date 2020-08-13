odoo.define('im_livechat/static/tests/helpers/mock_server.js', function (require) {
'use strict';

require('mail.MockServer'); // ensure mail overrides are applied first

const MockServer = require('web.MockServer');

MockServer.include({
    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * @override
     */
    _mockRouteMailInitMessaging() {
        const initMessaging = this._super(...arguments);

        const livechats = this._getRecords('mail.channel', [
            ['channel_type', '=', 'livechat'],
            ['is_pinned', '=', true],
            ['members', 'in', this.currentPartnerId],
        ]);
        initMessaging.channel_slots.channel_livechat = this._mockMailChannelChannelInfo(
            livechats.map(channel => channel.id)
        );

        return initMessaging;
    },
});

});
