/** @odoo-module **/

import '@im_livechat/../tests/helpers/mock_server'; // ensure mail overrides are applied first

import { patch } from "@web/core/utils/patch";
import { MockServer } from "@web/../tests/helpers/mock_server";

patch(MockServer.prototype, 'website_livechat', {
    /**
     * @override
     */
     async _performRPC(route, args) {
        if (route === '/web/dataset/call_button') {
            return this._mockCallButton(args);
        }
        return this._super(route, args);
    },
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
     * Overrides to add visitor information to livechat channels.
     *
     * @override
     */
    _mockMailChannelChannelInfo(ids) {
        const channelInfos = this._super(...arguments);
        for (const channelInfo of channelInfos) {
            const channel = this.getRecords('mail.channel', [['id', '=', channelInfo.id]])[0];
            if (channel.channel_type === 'livechat' && channelInfo.livechat_visitor_id) {
                const visitor = this.getRecords('website.visitor', [['id', '=', channelInfo.livechat_visitor_id]])[0];
                const country = this.getRecords('res.country', [['id', '=', visitor.country_id]])[0];
                channelInfo.visitor = {
                    country_code: country && country.code,
                    country_id: country && country.id,
                    display_name: visitor.display_name,
                    history: visitor.history, // TODO should be computed
                    id: visitor.id,
                    is_connected: visitor.is_connected,
                    lang_name: visitor.lang_name,
                    partner_id: visitor.partner_id,
                    website_name: visitor.website_name,
                };
            }
        }
        return channelInfos;
    },
    /**
     * @private
     * @param {integer[]} ids
     */
    _mockWebsiteVisitorActionSendChatRequest(ids) {
        const visitors = this.getRecords('website.visitor', [['id', 'in', ids]]);
        for (const visitor of visitors) {
            const country = visitor.country_id
                ? this.getRecords('res.country', [['id', '=', visitor.country_id]])
                : undefined;
            const visitor_name = `${visitor.display_name}${country ? `(${country.name})` : ''}`;
            const membersToAdd = [[0, 0, { partner_id: this.currentPartnerId }]];
            if (visitor.partner_id) {
                membersToAdd.push([0, 0, { partner_id: visitor.partner_id }]);
            } else {
                membersToAdd.push([0, 0, { partner_id: this.publicPartnerId }]);
            }
            const livechatId = this.pyEnv['mail.channel'].create({
                anonymous_name: visitor_name,
                channel_member_ids: membersToAdd,
                channel_type: 'livechat',
                livechat_operator_id: this.currentPartnerId,
            });
            // notify operator
            this.pyEnv['bus.bus']._sendone(this.currentPartner, 'website_livechat.send_chat_request',
                this._mockMailChannelChannelInfo([livechatId])[0]
            );
        }
    },
});
