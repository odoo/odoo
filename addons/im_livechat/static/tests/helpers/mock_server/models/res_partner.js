/** @odoo-module **/

import '@mail/../tests/helpers/mock_server/models/res_partner'; // ensure mail overrides are applied first

import { patch } from "@web/core/utils/patch";
import { MockServer } from "@web/../tests/helpers/mock_server";

patch(MockServer.prototype, 'im_livechat/models/res_partner', {
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
