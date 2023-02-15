/** @odoo-module **/

import { patch } from "@web/core/utils/patch";
import { MockServer } from "@web/../tests/helpers/mock_server";

patch(MockServer.prototype, 'im_livechat/controllers/main', {
    /**
     * @override
     */
    async _performRPC(route, args) {
        if (route === '/im_livechat/get_session') {
            const channel_id = args.channel_id;
            const anonymous_name = args.anonymous_name;
            const previous_operator_id = args.previous_operator_id;
            const context = args.context;
            return this._mockRouteImLivechatGetSession(channel_id, anonymous_name, previous_operator_id, context);
        }
        if (route === '/im_livechat/notify_typing') {
            const uuid = args.uuid;
            const is_typing = args.is_typing;
            const context = args.context;
            return this._mockRouteImLivechatNotifyTyping(uuid, is_typing, context);
        }
        return this._super(...arguments);
    },
    /**
     * Simulates the `/im_livechat/get_session` route.
     *
     * @private
     * @param {integer} channel_id
     * @param {string} anonymous_name
     * @param {integer} [previous_operator_id]
     * @param {Object} [context={}]
     * @returns {Object}
     */
     _mockRouteImLivechatGetSession(channel_id, anonymous_name, previous_operator_id, context = {}) {
        let user_id;
        let country_id;
        if ('mockedUserId' in context) {
            // can be falsy to simulate not being logged in
            user_id = context.mockedUserId;
        } else {
            user_id = this.currentUserId;
        }
        // don't use the anonymous name if the user is logged in
        if (user_id) {
            const user = this.getRecords('res.users', [['id', '=', user_id]])[0];
            country_id = user.country_id;
        } else {
            // simulate geoip
            const countryCode = context.mockedCountryCode;
            const country = this.getRecords('res.country', [['code', '=', countryCode]])[0];
            if (country) {
                country_id = country.id;
                anonymous_name = anonymous_name + ' (' + country.name + ')';
            }
        }
        return this._mockImLivechatChannel_openLivechatMailChannel(channel_id, anonymous_name, previous_operator_id, user_id, country_id);
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
