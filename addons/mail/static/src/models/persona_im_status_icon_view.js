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
         * @returns {FieldCommand}
         */
        _computePersona() {
            if (this.channelInvitationFormSelectablePartnerViewOwner) {
                return this.channelInvitationFormSelectablePartnerViewOwner.partner.persona;
            }
            if (this.channelMemberViewOwner) {
                return this.channelMemberViewOwner.channelMember.persona;
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
                return this.threadNeedactionPreviewViewOwner.thread.correspondent.persona;
            }
            if (this.threadPreviewViewOwner) {
                return this.threadPreviewViewOwner.thread.correspondent.persona;
            }
            return clear();
        },
    },
    fields: {
        channelInvitationFormSelectablePartnerViewOwner: one('ChannelInvitationFormSelectablePartnerView', {
            identifying: true,
            inverse: 'personaImStatusIconView',
            readonly: true,
        }),
        channelMemberViewOwner: one('ChannelMemberView', {
            identifying: true,
            inverse: 'personaImStatusIconView',
            readonly: true,
        }),
        composerSuggestionViewOwner: one('ComposerSuggestionView', {
            identifying: true,
            inverse: 'personaImStatusIconView',
            readonly: true,
        }),
        messageViewOwner: one('MessageView', {
            identifying: true,
            inverse: 'personaImStatusIconView',
            readonly: true,
        }),
        notificationRequestViewOwner: one('NotificationRequestView', {
            identifying: true,
            inverse: 'personaImStatusIconView',
            readonly: true,
        }),
        threadNeedactionPreviewViewOwner: one('ThreadNeedactionPreviewView', {
            identifying: true,
            inverse: 'personaImStatusIconView',
            readonly: true,
        }),
        threadPreviewViewOwner: one('ThreadPreviewView', {
            identifying: true,
            inverse: 'personaImStatusIconView',
            readonly: true,
        }),
        persona: one('Persona', {
            compute: '_computePersona',
            readonly: true,
            required: true,
        }),
    },
});
