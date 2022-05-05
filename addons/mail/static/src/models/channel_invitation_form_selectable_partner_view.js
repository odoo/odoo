/** @odoo-module **/

import { registerModel } from '@mail/model/model_core';
import { one } from '@mail/model/model_field';

registerModel({
    name: 'ChannelInvitationFormSelectablePartnerView',
    identifyingFields: ['channelInvitationFormOwner', 'partner'],
    fields: {
        channelInvitationFormOwner: one('ChannelInvitationForm', {
            inverse: 'selectablePartnerViews',
            readonly: true,
            required: true,
        }),
        partner: one('Partner', {
            inverse: 'channelInvitationFormSelectablePartnerViews',
            readonly: true,
            required: true,
        }),
    },
});
