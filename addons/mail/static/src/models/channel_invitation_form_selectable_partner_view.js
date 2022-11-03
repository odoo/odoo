/** @odoo-module **/

import { registerModel } from '@mail/model/model_core';
import { one } from '@mail/model/model_field';
import { clear } from '@mail/model/model_field_command';

registerModel({
    name: 'ChannelInvitationFormSelectablePartnerView',
    template: 'mail.ChannelInvitationFormSelectablePartnerView',
    templateGetter: 'channelInvitationFormSelectablePartnerView',
    fields: {
        channelInvitationFormOwner: one('ChannelInvitationForm', { identifying: true, inverse: 'selectablePartnerViews' }),
        partner: one('Partner', { identifying: true, inverse: 'channelInvitationFormSelectablePartnerViews' }),
        personaImStatusIconView: one('PersonaImStatusIconView', { inverse: 'channelInvitationFormSelectablePartnerViewOwner',
            compute() {
                return this.partner.isImStatusSet ? {} : clear();
            },
        }),
    },
});
