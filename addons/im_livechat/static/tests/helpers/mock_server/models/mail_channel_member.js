/** @odoo-module **/

import '@mail/../tests/helpers/mock_server/models/mail_channel_member'; // ensure mail overrides are applied first

import { patch } from "@web/core/utils/patch";
import { MockServer } from "@web/../tests/helpers/mock_server";

patch(MockServer.prototype, 'im_livechat/models/mail_channel_member', {
    /**
     * @override
     */
    _mockMailChannelMember_GetPartnerData(ids) {
        const [member] = this.getRecords('mail.channel.member', [['id', 'in', ids]]);
        const [channel] = this.getRecords('mail.channel', [['id', '=', member.channel_id]]);
        const [partner] = this.getRecords('res.partner', [['id', '=', member.partner_id]], { active_test: false });
        if (channel.channel_type === 'livechat') {
            const data = {
                'id': partner.id,
                'is_public': partner.is_public,
            };
            if (partner.user_livechat_username) {
                data['user_livechat_username'] = partner.user_livechat_username;
            } else {
                data['name'] = partner.name;
            }
            if (!partner.is_public) {
                const [country] = this.getRecords('res.country', [['id', '=', partner.country_id]]);
                data['country'] = country
                    ? {
                        'code': country.code,
                        'id': country.id,
                        'name': country.name,
                    }
                    : [['clear']];
            }
            return data;
        }
        return this._super(ids);
    },
});
