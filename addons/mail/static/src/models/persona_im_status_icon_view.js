/** @odoo-module **/

import { attr, one } from '@mail/model/model_field';
import { registerModel } from '@mail/model/model_core';
import { clear } from '@mail/model/model_field_command';
import { markEventHandled } from '@mail/utils/utils';

registerModel({
    name: 'PersonaImStatusIconView',
    identifyingMode: 'xor',
    recordMethods: {
        /**
         * @param {MouseEvent} ev
         */
        onClick(ev) {
            markEventHandled(ev, 'PersonaImStatusIcon.Click');
            if (!this.hasOpenChat || !this.persona.partner) {
                return;
            }
            this.persona.partner.openChat();
        },
    },
    fields: {
        channelInvitationFormSelectablePartnerViewOwner: one('ChannelInvitationFormSelectablePartnerView', {
            identifying: true,
            inverse: 'personaImStatusIconView',
        }),
        channelMemberViewOwner: one('ChannelMemberView', {
            identifying: true,
            inverse: 'personaImStatusIconView',
        }),
        channelPreviewViewOwner: one('ChannelPreviewView', {
            identifying: true,
            inverse: 'personaImStatusIconView',
        }),
        composerSuggestionViewOwner: one('ComposerSuggestionView', {
            identifying: true,
            inverse: 'personaImStatusIconView',
        }),
        hasBackground: attr({
            compute() {
                if (this.composerSuggestionViewOwner) {
                    return false;
                }
                return clear();
            },
            default: true,
        }),
        /**
         * Determines whether a click on this view should open a chat with the
         * corresponding persona.
         */
        hasOpenChat: attr({
            compute() {
                if (this.channelMemberViewOwner) {
                    return this.channelMemberViewOwner.hasOpenChat;
                }
                if (this.messageViewOwner) {
                    return this.messageViewOwner.hasAuthorOpenChat;
                }
                return clear();
            },
            default: false,
        }),
        messageViewOwner: one('MessageView', {
            identifying: true,
            inverse: 'personaImStatusIconView',
        }),
        notificationRequestViewOwner: one('NotificationRequestView', {
            identifying: true,
            inverse: 'personaImStatusIconView',
        }),
        persona: one('Persona', {
            compute() {
                if (this.channelInvitationFormSelectablePartnerViewOwner) {
                    return this.channelInvitationFormSelectablePartnerViewOwner.partner.persona;
                }
                if (this.channelMemberViewOwner) {
                    return this.channelMemberViewOwner.channelMember.persona;
                }
                if (this.channelPreviewViewOwner) {
                    return this.channelPreviewViewOwner.channel.correspondent.persona;
                }
                if (this.composerSuggestionViewOwner) {
                    return this.composerSuggestionViewOwner.suggestable.partner.persona;
                }
                if (this.messageViewOwner) {
                    if (this.messageViewOwner.message.author) {
                        return this.messageViewOwner.message.author.persona;
                    }
                    if (this.messageViewOwner.message.guestAuthor) {
                        return this.messageViewOwner.message.guestAuthor.persona;
                    }
                }
                if (this.notificationRequestViewOwner) {
                    return this.messaging.partnerRoot.persona;
                }
                if (this.threadNeedactionPreviewViewOwner) {
                    return this.threadNeedactionPreviewViewOwner.thread.channel.correspondent.persona;
                }
                return clear();
            },
            required: true,
        }),
        threadNeedactionPreviewViewOwner: one('ThreadNeedactionPreviewView', {
            identifying: true,
            inverse: 'personaImStatusIconView',
        }),
    },
});
