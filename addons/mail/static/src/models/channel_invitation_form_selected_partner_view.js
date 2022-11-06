/** @odoo-module **/

import { one, registerModel } from '@mail/model';

registerModel({
    name: 'ChannelInvitationFormSelectedPartnerView',
    template: 'mail.ChannelInvitationFormSelectedPartnerView',
    fields: {
        channelInvitationFormOwner: one('ChannelInvitationForm', { identifying: true, inverse: 'selectedPartnerViews' }),
        partner: one('Partner', { identifying: true, inverse: 'channelInvitationFormSelectedPartnerViews' }),
    },
});
