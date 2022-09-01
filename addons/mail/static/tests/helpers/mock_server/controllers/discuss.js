/** @odoo-module **/

import { patch } from "@web/core/utils/patch";
import { MockServer } from "@web/../tests/helpers/mock_server";

patch(MockServer.prototype, 'mail/controllers/discuss', {
    /**
     * @override
     */
    async _performRPC(route, args) {
        if (route === '/mail/channel/notify_typing') {
            const id = args.channel_id;
            const is_typing = args.is_typing;
            const context = args.context;
            return this._mockRouteMailChannelNotifyTyping(id, is_typing, context);
        }
        return this._super(route, args);
    },
    /**
     * Simulates the `/mail/channel/notify_typing` route.
     *
     * @private
     * @param {integer} channel_id
     * @param {integer} limit
     * @param {Object} [context={}]
     */
    async _mockRouteMailChannelNotifyTyping(channel_id, is_typing, context = {}) {
        const partnerId = context.mockedPartnerId || this.currentPartnerId;
        const [memberOfCurrentUser] = this.getRecords('mail.channel.member', [['channel_id', '=', channel_id], ['partner_id', '=', partnerId]]);
        this._mockMailChannelMember_NotifyTyping([memberOfCurrentUser.id], is_typing);
    },
});
