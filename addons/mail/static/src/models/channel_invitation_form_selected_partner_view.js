/** @odoo-module **/

import { registerModel } from '@mail/model/model_core';
import { one } from '@mail/model/model_field';

registerModel({
    name: 'ChannelInvitationFormSelectedPartnerView',
    identifyingFields: ['channelInvitationFormOwner', 'partner'],
    fields: {
        channelInvitationFormOwner: one('ChannelInvitationForm', {
            inverse: 'selectedPartnerViews',
            readonly: true,
            required: true,
        }),
        partner: one('Partner', {
            inverse: 'channelInvitationFormSelectedPartnerViews',
            readonly: true,
            required: true,
        }),
    },
});
