/** @odoo-module **/

import { patch } from "@web/core/utils/patch";
import { MockServer } from "@web/../tests/helpers/mock_server";

patch(MockServer.prototype, "im_livechat/controllers/main", {
    /**
     * @override
     */
    async _performRPC(route, args) {
        if (route === "/im_livechat/get_session") {
            const channel_id = args.channel_id;
            const anonymous_name = args.anonymous_name;
            const previous_operator_id = args.previous_operator_id;
            const persisted = args.persisted;
            const context = args.context;
            return this._mockRouteImLivechatGetSession(
                channel_id,
                anonymous_name,
                previous_operator_id,
                persisted,
                context
            );
        }
        if (route === "/im_livechat/init") {
            return this._mockRouteImLivechatInit(args.channel_id);
        }
        if (route === "/im_livechat/visitor_leave_session") {
            return this._mockRouteVisitorLeaveSession(args.uuid);
        }
        if (route === "/im_livechat/notify_typing") {
            const uuid = args.uuid;
            const is_typing = args.is_typing;
            const context = args.context;
            return this._mockRouteImLivechatNotifyTyping(uuid, is_typing, context);
        }
        if (route === "/im_livechat/chat_post") {
            const uuid = args.uuid;
            const message_content = args.message_content;
            const context = args.context;
            return this._mockRouteImLivechatChatPost(uuid, message_content, context);
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
    _mockRouteImLivechatGetSession(
        channel_id,
        anonymous_name,
        previous_operator_id,
        persisted,
        context = {}
    ) {
        let user_id;
        let country_id;
        if ("mockedUserId" in context) {
            // can be falsy to simulate not being logged in
            user_id = context.mockedUserId;
        } else {
            user_id = this.currentUserId;
        }
        // don't use the anonymous name if the user is logged in
        if (user_id) {
            const user = this.getRecords("res.users", [["id", "=", user_id]])[0];
            country_id = user.country_id;
        } else {
            // simulate geoip
            const countryCode = context.mockedCountryCode;
            const country = this.getRecords("res.country", [["code", "=", countryCode]])[0];
            if (country) {
                country_id = country.id;
                anonymous_name = anonymous_name + " (" + country.name + ")";
            }
        }
        return this._mockImLivechatChannel_openLivechatDiscussChannel(
            channel_id,
            anonymous_name,
            previous_operator_id,
            user_id,
            country_id,
            persisted
        );
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
        const [discussChannel] = this.getRecords("discuss.channel", [["uuid", "=", uuid]]);
        const partnerId = context.mockedPartnerId || this.currentPartnerId;
        const [memberOfCurrentUser] = this.getRecords("discuss.channel.member", [
            ["channel_id", "=", discussChannel.id],
            ["partner_id", "=", partnerId],
        ]);
        this._mockDiscussChannelMember_NotifyTyping([memberOfCurrentUser.id], is_typing);
    },
    /**
     * Simulates the `/im_livechat/chat_post` route.
     *
     * @private
     * @param {string} uuid
     * @param {string} message_content
     * @param {Object} [context={}]
     * @returns {Object} one key for list of followers and one for subtypes
     */
    async _mockRouteImLivechatChatPost(uuid, message_content, context = {}) {
        const channel = this.getRecords("discuss.channel", [["uuid", "=", uuid]])[0];
        if (!channel) {
            return false;
        }

        let user_id;
        // find the author from the user session
        if ("mockedUserId" in context) {
            // can be falsy to simulate not being logged in
            user_id = context.mockedUserId;
        } else {
            user_id = this.currentUserId;
        }
        let author_id;
        let email_from;
        if (user_id) {
            const author = this.getRecords("res.users", [["id", "=", user_id]])[0];
            author_id = author.partner_id;
            email_from = `${author.display_name} <${author.email}>`;
        } else {
            author_id = false;
            // simpler fallback than catchall_formatted
            email_from = channel.anonymous_name || "catchall@example.com";
        }
        // supposedly should convert plain text to html
        const body = message_content;
        // ideally should be posted with mail_create_nosubscribe=True
        return this._mockDiscussChannelMessagePost(
            channel.id,
            {
                author_id,
                email_from,
                body,
                message_type: "comment",
                subtype_xmlid: "mail.mt_comment",
            },
            context
        );
    },
    /**
     * Simulates the `/im_livechat/visitor_leave_session` route.
     *
     * @param {string} uuid
     */
    _mockRouteVisitorLeaveSession(uuid) {
        const channel = this.pyEnv["discuss.channel"].searchRead([["uuid", "=", uuid]]);
        if (!channel) {
            return;
        }
        this._mockDiscussChannel_closeLivechatSession(channel);
    },

    /**
     * Simulates the `/im_livechat/init` route.
     */
    _mockRouteImLivechatInit(channelId) {
        return {
            available_for_me: true,
            rule: {},
        };
    },
});
