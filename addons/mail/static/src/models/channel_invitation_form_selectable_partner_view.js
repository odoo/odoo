/** @odoo-module **/

import { registerModel } from '@mail/model/model_core';
import { one } from '@mail/model/model_field';
import { clear, insertAndReplace } from '@mail/model/model_field_command';

registerModel({
    name: 'ChannelInvitationFormSelectablePartnerView',
    identifyingFields: ['channelInvitationFormOwner', 'partner'],
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
            inverse: 'selectablePartnerViews',
            readonly: true,
            required: true,
        }),
        partner: one('Partner', {
            inverse: 'channelInvitationFormSelectablePartnerViews',
            readonly: true,
            required: true,
        }),
        personaImStatusIconView: one('PersonaImStatusIconView', {
            compute: '_computePersonaImStatusIconView',
            inverse: 'channelInvitationFormSelectablePartnerViewOwner',
            isCausal: true,
            readonly: true,
        }),
    },
});
