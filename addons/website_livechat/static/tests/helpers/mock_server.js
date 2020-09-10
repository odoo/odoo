odoo.define('website_livechat/static/tests/helpers/mock_server.js', function (require) {
'use strict';

require('im_livechat/static/tests/helpers/mock_server.js'); // ensure mail overrides are applied first

const MockServer = require('web.MockServer');

MockServer.include({
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
    /**
     * @private
     * @param {integer[]} ids
     */
    _mockWebsiteVisitorActionSendChatRequest(ids) {
        const visitors = this._getRecords('website.visitor', [['id', 'in', ids]]);
        for (const visitor of visitors) {
            const country = visitor.country_id
                ? this._getRecords('res.country', [['id', '=', visitor.country_id]])
                : undefined;
            const visitor_name = `${visitor.display_name}${country ? `(${country.name})` : ''}`;
            const members = [this.currentPartnerId];
            if (visitor.partner_id) {
                members.push(visitor.partner_id);
            } else {
                members.push(this.publicPartnerId);
            }
            const livechatId = this._mockCreate('mail.channel', {
                anonymous_name: visitor_name,
                channel_type: 'livechat',
                livechat_operator_id: this.currentPartnerId,
                members,
                public: 'private',
            });
            // notify operator
            const channelInfo = this._mockMailChannelChannelInfo([livechatId], 'send_chat_request')[0];
            const notification = [[false, 'res.partner', this.currentPartnerId], channelInfo];
            this._widget.call('bus_service', 'trigger', 'notification', [notification]);
        }
    },
});

});
