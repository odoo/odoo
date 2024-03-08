import { patch } from "@web/core/utils/patch";
import { MockServer } from "@web/../tests/helpers/mock_server";

patch(MockServer.prototype, {
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
                parseInt(previous_operator_id),
                persisted,
                context
            );
        }
        if (route === "/im_livechat/init") {
            return this._mockRouteImLivechatInit(args.channel_id);
        }
        if (route === "/im_livechat/visitor_leave_session") {
            return this._mockRouteVisitorLeaveSession(args.channel_id);
        }
        if (route === "/im_livechat/notify_typing") {
            const channelid = args.channel_id;
            const is_typing = args.is_typing;
            return this._mockRouteImLivechatNotifyTyping(channelid, is_typing);
        }
        if (route === "/im_livechat/feedback") {
            const { channel_id, rate, reason } = args;
            return this._mockRouteImLivechatFeedback(channel_id, rate, reason);
        }
        if (route === "/im_livechat/email_livechat_transcript") {
            return true;
        }
        if (route === "/im_livechat/chat_history") {
            return this._mockRouteImLivechatChatHistory(args.channel_id, args.last_id, args.limit);
        }
        return super._performRPC(...arguments);
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
        let country_id;
        // don't use the anonymous name if the user is logged in
        if (this.pyEnv.currentUser && !this.pyEnv.currentUser._is_public()) {
            country_id = this.pyEnv.currentUser.country_id;
        } else {
            // simulate geoip
            const countryCode = context.mockedCountryCode;
            const country = this.getRecords("res.country", [["code", "=", countryCode]])[0];
            if (country) {
                country_id = country.id;
                anonymous_name = anonymous_name + " (" + country.name + ")";
            }
        }
        const channelVals = this._mockImLivechatChannel_getLivechatDiscussChannelVals(
            channel_id,
            anonymous_name,
            previous_operator_id,
            country_id,
            persisted
        );
        if (!channelVals) {
            return false;
        }
        if (!persisted) {
            const [operatorPartner] = this.pyEnv["res.partner"].searchRead([
                ["id", "=", channelVals.livechat_operator_id],
            ]);
            const res = this._mockResUsers__init_store_data();
            return Object.assign(res, {
                Thread: {
                    id: -1,
                    model: "discuss.channel",
                    isLoaded: true,
                    name: channelVals["name"],
                    chatbot_current_step_id: channelVals.chatbot_current_step_id,
                    state: "open",
                    operator: this._mockResPartnerMailPartnerFormat([operatorPartner.id]).get(
                        operatorPartner.id
                    ),
                    channel_type: "livechat",
                },
            });
        }
        const channelId = this.pyEnv["discuss.channel"].create(channelVals);
        this._mockDiscussChannel__findOrCreatePersonaForChannel(
            channelId,
            this._mock__getGuestName()
        );
        const [guestMemberId] = this.pyEnv["discuss.channel.member"].search([
            ["channel_id", "=", channelId],
            ["guest_id", "!=", false],
        ]);
        this.pyEnv["discuss.channel.member"].write([guestMemberId], { fold_state: "open" });
        const res = this._mockResUsers__init_store_data();
        return Object.assign(res, {
            Thread: {
                isLoaded: true,
                ...this._mockDiscussChannelChannelInfo([channelId])[0],
            },
        });
    },
    _mock__getGuestName() {
        return "Visitor";
    },
    /**
     * Simulates the `/im_livechat/notify_typing` route.
     *
     * @private
     * @param {string} channelId
     * @param {boolean} is_typing
     * @param {Object} [context={}]
     */
    _mockRouteImLivechatNotifyTyping(channelId, is_typing) {
        const [channel] = this.pyEnv["discuss.channel"].searchRead([["id", "=", channelId]]);
        const memberOfCurrentUser = this._mockDiscussChannelMember__getAsSudoFromContext(
            channel.id
        );
        this._mockDiscussChannelMember_NotifyTyping([memberOfCurrentUser.id], is_typing);
    },
    /**
     * Simulates the `/im_livechat/visitor_leave_session` route.
     *
     * @param {string} channelId
     */
    _mockRouteVisitorLeaveSession(channelId) {
        const channel = this.pyEnv["discuss.channel"].searchRead([["id", "=", channelId]]);
        if (!channel) {
            return;
        }
        this._mockDiscussChannel_closeLivechatSession(channel);
    },

    /**
     * Simulates the `/im_livechat/feedback` route.
     *
     * @param {string} channelId
     * @param {number} rate
     * @param {string|undefined} reason
     * @returns
     */
    _mockRouteImLivechatFeedback(channelId, rate, reason) {
        let [channel] = this.pyEnv["discuss.channel"].searchRead([["id", "=", channelId]]);
        if (!channel) {
            return false;
        }
        const values = {
            rating: rate,
            consumed: true,
            feedback: reason,
            is_internal: false,
            res_id: channel.id,
            res_model: "discuss.channel",
            rated_partner_id: channel.channel_partner_ids[0],
        };
        if (channel.rating_ids.length === 0) {
            this.pyEnv["rating.rating"].create(values);
        } else {
            this.pyEnv["rating.rating"].write([channel.rating_ids[0]], values);
        }
        [channel] = this.pyEnv["discuss.channel"].searchRead([["id", "=", channelId]]);
        return channel.rating_ids[0];
    },

    /**
     * Simulates the `/im_livechat/chat_history` route.
     */
    _mockRouteImLivechatChatHistory(channelId, lastId, limit = 20) {
        const [channel] = this.pyEnv["discuss.channel"].searchRead([["id", "=", channelId]]);
        if (!channel) {
            return [];
        }
        return this._mockDiscussChannel_channel_fetch_message(channel.id, lastId, limit);
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
