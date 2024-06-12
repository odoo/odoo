/** @odoo-module **/

import { Command } from "@mail/../tests/helpers/command";

import { patch } from "@web/core/utils/patch";
import { MockServer } from "@web/../tests/helpers/mock_server";

patch(MockServer.prototype, {
    /**
     * @private
     * @param {integer[]} ids
     */
    _mockWebsiteVisitorActionSendChatRequest(ids) {
        const visitors = this.getRecords("website.visitor", [["id", "in", ids]]);
        for (const visitor of visitors) {
            const country = visitor.country_id
                ? this.getRecords("res.country", [["id", "=", visitor.country_id]])
                : undefined;
            const visitor_name = `${visitor.display_name}${country ? `(${country.name})` : ""}`;
            const membersToAdd = [[0, 0, { partner_id: this.pyEnv.currentPartnerId }]];
            if (visitor.partner_id) {
                membersToAdd.push([0, 0, { partner_id: visitor.partner_id }]);
            }
            const livechatId = this.pyEnv["discuss.channel"].create({
                anonymous_name: visitor_name,
                channel_member_ids: membersToAdd,
                channel_type: "livechat",
                livechat_operator_id: this.pyEnv.currentPartnerId,
            });
            if (!visitor.partner_id) {
                const guestId = this.pyEnv["mail.guest"].create({ name: `Visitor #${visitor.id}` });
                this.pyEnv["discuss.channel"].write([livechatId], {
                    channel_member_ids: [Command.create({ guest_id: guestId })],
                });
            }
            // notify operator
            this.pyEnv["bus.bus"]._sendone(
                this.pyEnv.currentPartner,
                "website_livechat.send_chat_request",
                this._mockDiscussChannelChannelInfo([livechatId])[0]
            );
        }
    },
});
