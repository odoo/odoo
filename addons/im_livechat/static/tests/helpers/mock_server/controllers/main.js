/** @odoo-module **/

import '@mail/../tests/helpers/mock_server'; // ensure mail overrides are applied first

import { patch } from "@web/core/utils/patch";
import { MockServer } from "@web/../tests/helpers/mock_server";

patch(MockServer.prototype, 'im_livechat/controllers/main', {
    /**
     * @override
     */
    async _performRPC(route, args) {
        if (route === '/im_livechat/notify_typing') {
            const uuid = args.uuid;
            const is_typing = args.is_typing;
            const context = args.context;
            return this._mockRouteImLivechatNotifyTyping(uuid, is_typing, context);
        }
        return this._super(...arguments);
    },
    /**
     * Simulates the `/im_livechat/notify_typing` route.
     *
     * @private
     * @param {string} uuid
     * @param {boolean} is_typing
     * @param {Object} [context={}]
     */
    _mockRouteImLivechatNotifyTyping(uuid, is_typing, context = {}) {
        const [mailChannel] = this.getRecords('mail.channel', [['uuid', '=', uuid]]);
        const partnerId = context.mockedPartnerId || this.currentPartnerId;
        const [memberOfCurrentUser] = this.getRecords('mail.channel.member', [['channel_id', '=', mailChannel.id], ['partner_id', '=', partnerId]]);
        this._mockMailChannelMember_NotifyTyping([memberOfCurrentUser.id], is_typing);
    },
});
