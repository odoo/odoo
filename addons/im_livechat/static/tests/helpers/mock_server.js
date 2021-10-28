/** @odoo-module **/

import '@mail/../tests/helpers/mock_server'; // ensure mail overrides are applied first

import MockServer from 'web.MockServer';

MockServer.include({
    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * @override
     */
    async _performRpc(route, args) {
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
            const user = this._getRecords('res.users', [['id', '=', user_id]])[0];
            country_id = user.country_id;
        } else {
            // simulate geoip
            const countryCode = context.mockedCountryCode;
            const country = this._getRecords('res.country', [['code', '=', countryCode]])[0];
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
     * @param {Object} [context]
     */
    _mockRouteImLivechatNotifyTyping(uuid, is_typing, context) {
        const mailChannel = this._getRecords('mail.channel', [['uuid', '=', uuid]])[0];
        this._mockMailChannelNotifyTyping([mailChannel.id], is_typing, context);
    },

    //--------------------------------------------------------------------------
    // Private Mocked Methods
    //--------------------------------------------------------------------------

    /**
     * Simulates `_channel_get_livechat_visitor_info` on `mail.channel`.
     *
     * @private
     * @param {integer[]} ids
     * @returns {Object}
     */
    _mockMailChannel_ChannelGetLivechatVisitorInfo(ids) {
        const id = ids[0]; // ensure_one
        const mailChannel = this._getRecords('mail.channel', [['id', '=', id]])[0];
        // remove active test to ensure public partner is taken into account
        let members = this._getRecords(
            'res.partner',
            [['id', 'in', mailChannel.members]],
            { active_test: false },
        );
        members = members.filter(member => member.id !== mailChannel.livechat_operator_id);
        if (members.length === 0 && mailChannel.livechat_operator_id) {
            // operator probably testing the livechat with his own user
            members = [mailChannel.livechat_operator_id];
        }
        if (members.length > 0 && members[0].id !== this.publicPartnerId) {
            // legit non-public partner
            const country = this._getRecords('res.country', [['id', '=', members[0].country_id]])[0];
            return {
                'country': country ? [country.id, country.name] : false,
                'id': members[0].id,
                'name': members[0].name,
            };
        }
        return {
            'country': false,
            'id': false,
            'name': mailChannel.anonymous_name || "Visitor",
        };
    },
    /**
     * @override
     */
    _mockMailChannelChannelInfo(ids) {
        const channelInfos = this._super(...arguments);
        for (const channelInfo of channelInfos) {
            const channel = this._getRecords('mail.channel', [['id', '=', channelInfo.id]])[0];
            // add the last message date
            if (channel.channel_type === 'livechat') {
                // add the operator id
                if (channel.livechat_operator_id) {
                    const operator = this._getRecords('res.partner', [['id', '=', channel.livechat_operator_id]])[0];
                    // livechat_username ignored for simplicity
                    channelInfo.operator_pid = [operator.id, operator.display_name.replace(',', '')];
                }
                // add the anonymous or partner name
                channelInfo.livechat_visitor = this._mockMailChannel_ChannelGetLivechatVisitorInfo([channel.id]);
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
        const livechatChannel = this._getRecords('im_livechat.channel', [['id', '=', id]])[0];
        const users = this._getRecords('res.users', [['id', 'in', livechatChannel.user_ids]]);
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
        const members = [[4, operator_partner_id]];
        let visitor_user;
        if (user_id) {
            const visitor_user = this._getRecords('res.users', [['id', '=', user_id]])[0];
            if (visitor_user && visitor_user.active) {
                // valid session user (not public)
                members.push([4, visitor_user.partner_id.id]);
            }
        } else {
            // for simplicity of not having mocked channel.partner, add public partner here
            members.push([4, this.publicPartnerId]);
        }
        const membersName = [
            visitor_user ? visitor_user.display_name : anonymous_name,
            operator.livechat_username ? operator.livechat_username : operator.name,
        ];
        return {
            // Limitation of mocked models not having channel.partner: is_pinned
            // is not supposed to be false for the visitor but must be false for
            // the operator (writing on channel_partner_ids does not trigger the
            // defaults that would set it to true) and here operator and visitor
            // can't be differentiated in that regard.
            'is_pinned': false,
            'members': members, // channel_partner_ids
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
        const mailChannelId = this._mockCreate('mail.channel', mailChannelVals);
        this._mockMailChannel_broadcast([mailChannelId], [operator.partner_id]);
        return this._mockMailChannelChannelInfo([mailChannelId])[0];
    },
    /**
     * @override
     */
    _mockResPartner_GetChannelsAsMember(ids) {
        const partner = this._getRecords('res.partner', [['id', 'in', ids]])[0];
        const livechats = this._getRecords('mail.channel', [
            ['channel_type', '=', 'livechat'],
            ['is_pinned', '=', true],
            ['members', 'in', partner.id],
        ]);
        return [
            ...this._super(ids),
            ...livechats,
        ];
    },
});
