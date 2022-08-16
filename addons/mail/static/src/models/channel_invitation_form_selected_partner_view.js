/** @odoo-module **/

import { registerModel } from '@mail/model/model_core';
import { one } from '@mail/model/model_field';

registerModel({
    name: 'ChannelInvitationFormSelectedPartnerView',
    fields: {
        channelInvitationFormOwner: one('ChannelInvitationForm', {
            identifying: true,
            inverse: 'selectedPartnerViews',
            readonly: true,
            required: true,
        }),
        partner: one('Partner', {
            identifying: true,
            inverse: 'channelInvitationFormSelectedPartnerViews',
            readonly: true,
            required: true,
        }),
    },
});
