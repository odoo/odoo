/** @odoo-module **/

import { registerModel } from '@mail/model/model_core';
import { attr, one } from '@mail/model/model_field';
import { clear, insertAndReplace } from '@mail/model/model_field_command';
import { isEventHandled } from '@mail/utils/utils'

registerModel({
    name: 'ChannelMemberView',
    identifyingFields: ['channelMemberListCategoryViewOwner', 'channelMember'],
    recordMethods: {
        /**
         * Handles click on channel member in the member list of this channel.
         *
         * @param {MouseEvent} ev
         */
        onClickMember(ev) {
            if (isEventHandled(ev, 'PersonaImStatusIcon.Click') || !this.channelMember.partner) {
                return;
            }
            this.channelMember.partner.openChat();
        },
        /**
         * @private
         * @returns {Boolean}
         */
        _computeHasOpenChat() {
            return this.channelMember.partner ? true : false;
        },
        /**
         * @private
         * @returns {string}
         */
        _computeMemberTitleText() {
            return this.hasOpenChat ? this.env._t("Open chat") : '';
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
        hasOpenChat: attr({
            compute: '_computeHasOpenChat',
        }),
        memberTitleText: attr({
            compute: '_computeMemberTitleText',
        }),
        personaImStatusIconView: one('PersonaImStatusIconView', {
            compute: '_computePersonaImStatusIconView',
            inverse: 'channelMemberViewOwner',
            isCausal: true,
            readonly: true,
        }),
    },
});
