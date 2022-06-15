/** @odoo-module **/

import { registerModel } from '@mail/model/model_core';
import { one } from '@mail/model/model_field';
import { clear, insertAndReplace } from '@mail/model/model_field_command';

registerModel({
    name: 'ChannelMemberView',
    identifyingFields: ['channelMemberListCategoryViewOwner', 'channelMember'],
    recordMethods: {
        /**
         * Handles click on the avatar of the channel member in the member list
         * of this channel.
         */
        onClickMemberAvatar() {
            if (!this.channelMember.partner) {
                return;
            }
            this.channelMember.partner.openChat();
        },
        /**
         * Handles click on the name of the channel member in the member list of
         * this channel.
         */
        onClickMemberName() {
            if (!this.channelMember.partner) {
                return;
            }
            this.channelMember.partner.openProfile();
        },
        /**
         * @private
         * @returns {FieldCommand}
         */
        _computePersonaImStatusIconView() {
            return this.channelMember.partner && this.channelMember.partner.isImStatusSet ? insertAndReplace() : clear();
        },
    },
    fields: {
        channelMemberListCategoryViewOwner: one('ChannelMemberListCategoryView', {
            inverse: 'channelMemberViews',
            readonly: true,
            required: true,
        }),
        channelMember: one('ChannelMember', {
            inverse: 'channelMemberViews',
            readonly: true,
            required: true,
        }),
        personaImStatusIconView: one('PersonaImStatusIconView', {
            compute: '_computePersonaImStatusIconView',
            inverse: 'channelMemberViewOwner',
            isCausal: true,
            readonly: true,
        }),
    },
});
