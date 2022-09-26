/** @odoo-module **/

import '@mail/../tests/helpers/mock_server/models/mail_channel'; // ensure mail overrides are applied first

import { patch } from "@web/core/utils/patch";
import { MockServer } from "@web/../tests/helpers/mock_server";

patch(MockServer.prototype, 'im_livechat/models/mail_channel', {
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
});
