/** @odoo-module **/

import { registerModel } from '@mail/model/model_core';
import { one } from '@mail/model/model_field';
import { clear, insertAndReplace } from '@mail/model/model_field_command';

registerModel({
    name: 'ChannelInvitationFormSelectablePartnerView',
    recordMethods: {
        /**
         * @private
         * @returns {FieldCommand}
         */
        _computePersonaImStatusIconView() {
            return this.partner.isImStatusSet ? insertAndReplace() : clear();
        },
    },
    fields: {
        channelInvitationFormOwner: one('ChannelInvitationForm', {
            identifying: true,
            inverse: 'selectablePartnerViews',
        }),
        partner: one('Partner', {
            identifying: true,
            inverse: 'channelInvitationFormSelectablePartnerViews',
        }),
        personaImStatusIconView: one('PersonaImStatusIconView', {
            compute: '_computePersonaImStatusIconView',
            inverse: 'channelInvitationFormSelectablePartnerViewOwner',
            isCausal: true,
            readonly: true,
        }),
    },
});
