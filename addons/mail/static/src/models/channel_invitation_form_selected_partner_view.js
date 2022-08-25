/** @odoo-module **/

import { registerModel } from '@mail/model/model_core';
import { one } from '@mail/model/model_field';

registerModel({
    name: 'ChannelInvitationFormSelectedPartnerView',
    fields: {
        channelInvitationFormOwner: one('ChannelInvitationForm', {
            identifying: true,
            inverse: 'selectedPartnerViews',
        }),
        partner: one('Partner', {
            identifying: true,
            inverse: 'channelInvitationFormSelectedPartnerViews',
        }),
    },
});
