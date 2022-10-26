/** @odoo-module **/

import { registerModel } from '@mail/model/model_core';
import { attr, one } from '@mail/model/model_field';
import { clear } from '@mail/model/model_field_command';
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
            compute() {
                return this.channelMember.persona.partner ? true : false;
            },
        }),
        memberTitleText: attr({
            compute() {
                return this.hasOpenChat ? this.env._t("Open chat") : '';
            },
        }),
        personaImStatusIconView: one('PersonaImStatusIconView', {
            compute() {
                if (this.channelMember.persona.guest && this.channelMember.persona.guest.im_status) {
                    return {};
                }
                return this.channelMember.persona.partner && this.channelMember.persona.partner.isImStatusSet ? {} : clear();
            },
            inverse: 'channelMemberViewOwner',
        }),
    },
});
