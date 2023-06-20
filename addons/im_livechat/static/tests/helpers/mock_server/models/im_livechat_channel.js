/* @odoo-module */

import { patch } from "@web/core/utils/patch";
import { MockServer } from "@web/../tests/helpers/mock_server";

patch(MockServer.prototype, "im_livechat/models/im_livechat_channel", {
    /**
     * Simulates `_compute_available_operator_ids` on `im_livechat.channel`.
     *
     * @private
     * @param {integer} id
     * @returns {Object}
     */
    _mockImLivechatChannel__computeAvailableOperatorIds(id) {
        const livechatChannel = this.getRecords("im_livechat.channel", [["id", "=", id]])[0];
        const users = this.getRecords("res.users", [["id", "in", livechatChannel.user_ids]]);
        return users.filter((user) => user.im_status === "online");
    },
    /**
     * Simulates `_get_livechat_discuss_channel_vals` on `im_livechat.channel`.
     *
     * @private
     * @param {integer} id
     * @returns {Object}
     */
    _mockImLivechatChannel_getLivechatDiscussChannelVals(
        id,
        anonymous_name,
        operator,
        user_id,
        country_id
    ) {
        // partner to add to the discuss.channel
        const operator_partner_id = operator.partner_id;
        const membersToAdd = [
            [
                0,
                0,
                {
                    is_pinned: false,
                    partner_id: operator_partner_id,
                },
            ],
        ];
        let visitor_user;
        if (user_id) {
            const visitor_user = this.getRecords("res.users", [["id", "=", user_id]])[0];
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
            channel_partner_ids: [operator_partner_id],
            channel_member_ids: membersToAdd,
            livechat_active: true,
            livechat_operator_id: operator_partner_id,
            livechat_channel_id: id,
            anonymous_name: user_id ? false : anonymous_name,
            country_id: country_id,
            channel_type: "livechat",
            name: membersName.join(" "),
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
        const availableUsers = this._mockImLivechatChannel__computeAvailableOperatorIds(id);
        return availableUsers[0];
    },
    /**
     * Simulates `_open_livechat_discuss_channel` on `im_livechat.channel`.
     *
     * @private
     * @param {integer} id
     * @param {string} anonymous_name
     * @param {integer} [previous_operator_id]
     * @param {integer} [user_id]
     * @param {integer} [country_id]
     * @returns {Object}
     */
    _mockImLivechatChannel_openLivechatDiscussChannel(
        id,
        anonymous_name,
        previous_operator_id,
        user_id,
        country_id,
        persisted
    ) {
        let operator;
        if (previous_operator_id) {
            const availableUsers = this._mockImLivechatChannel__computeAvailableOperatorIds(id);
            operator = availableUsers.find((user) => user.partner_id === previous_operator_id);
        }
        if (!operator) {
            operator = this._mockImLivechatChannel_getRandomOperator(id);
        }
        if (!operator) {
            // no one available
            return false;
        }
        // create the session, and add the link with the given channel
        const discussChannelVals = this._mockImLivechatChannel_getLivechatDiscussChannelVals(
            id,
            anonymous_name,
            operator,
            user_id,
            country_id
        );
        if (persisted) {
            const discussChannelId = this.pyEnv["discuss.channel"].create(discussChannelVals);
            this._mockDiscussChannel_broadcast([discussChannelId], [operator.partner_id]);
            return this._mockDiscussChannelChannelInfo([discussChannelId])[0];
        }
        return {
            name: discussChannelVals["name"],
            chatbot_current_step_id: discussChannelVals["chatbot_current_step_id"],
            state: "open",
            operator_pid: [operator.partner_id, operator.name],
        };
    },
});
