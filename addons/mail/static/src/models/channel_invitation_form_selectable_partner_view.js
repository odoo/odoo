/** @odoo-module **/

import { clear, one, registerModel } from '@mail/model';

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
