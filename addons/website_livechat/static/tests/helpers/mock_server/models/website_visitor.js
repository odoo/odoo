/** @odoo-module **/

import { patch } from "@web/core/utils/patch";
import { MockServer } from "@web/../tests/helpers/mock_server";

patch(MockServer.prototype, 'website_livechat/models/website_visitor', {
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
            this.pyEnv['bus.bus']._sendone(this.pyEnv.currentPartner, 'website_livechat.send_chat_request',
                this._mockMailChannelChannelInfo([livechatId])[0]
            );
        }
    },
});
