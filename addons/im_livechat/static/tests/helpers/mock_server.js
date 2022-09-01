/** @odoo-module **/

import '@mail/../tests/helpers/mock_server'; // ensure mail overrides are applied first

import { patch } from "@web/core/utils/patch";
import { MockServer } from "@web/../tests/helpers/mock_server";

patch(MockServer.prototype, 'im_livechat', {
    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

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
        return this._super(...arguments);
    },

    //--------------------------------------------------------------------------
    // Private Mocked Routes
    //--------------------------------------------------------------------------

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

    //--------------------------------------------------------------------------
    // Private Mocked Methods
    //--------------------------------------------------------------------------

    /**
     * @override
     */
    _mockMailChannelChannelInfo(ids) {
        const channelInfos = this._super(...arguments);
        for (const channelInfo of channelInfos) {
            const channel = this.getRecords('mail.channel', [['id', '=', channelInfo.id]])[0];
            channelInfo['channel']['anonymous_name'] = channel.anonymous_name;
            // add the last message date
            if (channel.channel_type === 'livechat') {
                // add the operator id
                if (channel.livechat_operator_id) {
                    const operator = this.getRecords('res.partner', [['id', '=', channel.livechat_operator_id]])[0];
                    // livechat_username ignored for simplicity
                    channelInfo.operator_pid = [operator.id, operator.display_name.replace(',', '')];
                }
            }
        }
        return channelInfos;
    },
    /**
     * Simulates `_get_available_users` on `im_livechat.channel`.
     *
     * @private
     * @param {integer} id
     * @returns {Object}
     */
    _mockImLivechatChannel_getAvailableUsers(id) {
        const livechatChannel = this.getRecords('im_livechat.channel', [['id', '=', id]])[0];
        const users = this.getRecords('res.users', [['id', 'in', livechatChannel.user_ids]]);
        return users.filter(user => user.im_status === 'online');
    },
    /**
     * Simulates `_get_livechat_mail_channel_vals` on `im_livechat.channel`.
     *
     * @private
     * @param {integer} id
     * @returns {Object}
     */
    _mockImLivechatChannel_getLivechatMailChannelVals(id, anonymous_name, operator, user_id, country_id) {
        // partner to add to the mail.channel
        const operator_partner_id = operator.partner_id;
        const membersToAdd = [[0, 0, {
            is_pinned: false,
            partner_id: operator_partner_id,
        }]];
        let visitor_user;
        if (user_id) {
            const visitor_user = this.getRecords('res.users', [['id', '=', user_id]])[0];
            if (visitor_user && visitor_user.active && visitor_user !== operator) {
                // valid session user (not public)
                membersToAdd.push([0, 0, { partner_id: visitor_user.partner_id.id }]);
            }
        } else {
            membersToAdd.push([0, 0, { partner_id: this.publicPartnerId }]);
        }
        const membersName = [
            visitor_user ? visitor_user.display_name : anonymous_name,
            operator.livechat_username ? operator.livechat_username : operator.name,
        ];
        return {
            'channel_member_ids': membersToAdd,
            'livechat_active': true,
            'livechat_operator_id': operator_partner_id,
            'livechat_channel_id': id,
            'anonymous_name': user_id ? false : anonymous_name,
            'country_id': country_id,
            'channel_type': 'livechat',
            'name': membersName.join(' '),
            'public': 'private',
        };
    },
    /**
     * Simulates `_get_random_operator` on `im_livechat.channel`.
     * Simplified mock implementation: returns the first available operator.
     *
     * @private
     * @param {integer} id
     * @returns {Object}
     */
    _mockImLivechatChannel_getRandomOperator(id) {
        const availableUsers = this._mockImLivechatChannel_getAvailableUsers(id);
        return availableUsers[0];
    },
    /**
     * Simulates `_open_livechat_mail_channel` on `im_livechat.channel`.
     *
     * @private
     * @param {integer} id
     * @param {string} anonymous_name
     * @param {integer} [previous_operator_id]
     * @param {integer} [user_id]
     * @param {integer} [country_id]
     * @returns {Object}
     */
    _mockImLivechatChannel_openLivechatMailChannel(id, anonymous_name, previous_operator_id, user_id, country_id) {
        let operator;
        if (previous_operator_id) {
            const availableUsers = this._mockImLivechatChannel_getAvailableUsers(id);
            operator = availableUsers.find(user => user.partner_id === previous_operator_id);
        }
        if (!operator) {
            operator = this._mockImLivechatChannel_getRandomOperator(id);
        }
        if (!operator) {
            // no one available
            return false;
        }
        // create the session, and add the link with the given channel
        const mailChannelVals = this._mockImLivechatChannel_getLivechatMailChannelVals(id, anonymous_name, operator, user_id, country_id);
        const mailChannelId = this.pyEnv['mail.channel'].create(mailChannelVals);
        this._mockMailChannel_broadcast([mailChannelId], [operator.partner_id]);
        return this._mockMailChannelChannelInfo([mailChannelId])[0];
    },
    /**
     * @override
     */
    _mockResPartner_GetChannelsAsMember(ids) {
        const partner = this.getRecords('res.partner', [['id', 'in', ids]])[0];
        const members = this.getRecords('mail.channel.member', [['partner_id', '=', partner.id], ['is_pinned', '=', true]]);
        const livechats = this.getRecords('mail.channel', [
            ['channel_type', '=', 'livechat'],
            ['channel_member_ids', 'in', members.map(member => member.id)],
        ]);
        return [
            ...this._super(ids),
            ...livechats,
        ];
    },
});
