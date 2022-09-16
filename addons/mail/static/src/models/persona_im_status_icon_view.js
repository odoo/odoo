/** @odoo-module **/

import { one } from '@mail/model/model_field';
import { registerModel } from '@mail/model/model_core';
import { clear } from '@mail/model/model_field_command';

registerModel({
    name: 'PersonaImStatusIconView',
    identifyingMode: 'xor',
    recordMethods: {
        /**
         * @private
         * @returns {FieldCommand|Persona}
         */
        _computePersona() {
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
        messageViewOwner: one('MessageView', {
            identifying: true,
            inverse: 'personaImStatusIconView',
        }),
        notificationRequestViewOwner: one('NotificationRequestView', {
            identifying: true,
            inverse: 'personaImStatusIconView',
        }),
        persona: one('Persona', {
            compute: '_computePersona',
            required: true,
        }),
        threadNeedactionPreviewViewOwner: one('ThreadNeedactionPreviewView', {
            identifying: true,
            inverse: 'personaImStatusIconView',
        }),
    },
});
