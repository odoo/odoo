/** @odoo-module **/

import { registerModel } from '@mail/model/model_core';
import { attr, one } from '@mail/model/model_field';
import { clear, insertAndReplace } from '@mail/model/model_field_command';
import { isEventHandled } from '@mail/utils/utils';

registerModel({
    name: 'ChannelMemberView',
    recordMethods: {
        /**
         * Handles click on channel member in the member list of this channel.
         *
         * @param {MouseEvent} ev
         */
        onClickMember(ev) {
            if (isEventHandled(ev, 'PersonaImStatusIcon.Click') || !this.channelMember.persona.partner) {
                return;
            }
            this.channelMember.persona.partner.openChat();
        },
        /**
         * @private
         * @returns {Boolean}
         */
        _computeHasOpenChat() {
            return this.channelMember.persona.partner ? true : false;
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
            if (this.channelMember.persona.guest && this.channelMember.persona.guest.im_status) {
                return insertAndReplace();
            }
            return this.channelMember.persona.partner && this.channelMember.persona.partner.isImStatusSet ? insertAndReplace() : clear();
        },
    },
    fields: {
        channelMemberListCategoryViewOwner: one('ChannelMemberListCategoryView', {
            identifying: true,
            inverse: 'channelMemberViews',
        }),
        channelMember: one('ChannelMember', {
            identifying: true,
            inverse: 'channelMemberViews',
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
