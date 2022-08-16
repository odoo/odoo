/** @odoo-module **/

import { one } from '@mail/model/model_field';
import { registerModel } from '@mail/model/model_core';
import { clear, replace } from '@mail/model/model_field_command';

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
                return replace(this.channelInvitationFormSelectablePartnerViewOwner.partner.persona);
            }
            if (this.channelMemberViewOwner) {
                return replace(this.channelMemberViewOwner.channelMember.persona);
            }
            if (this.composerSuggestionViewOwner) {
                return replace(this.composerSuggestionViewOwner.suggestable.partner.persona);
            }
            if (this.messageViewOwner) {
                if (this.messageViewOwner.message.author) {
                    return replace(this.messageViewOwner.message.author.persona);
                }
                if (this.messageViewOwner.message.guestAuthor) {
                    return replace(this.messageViewOwner.message.guestAuthor.persona);
                }
            }
            if (this.notificationRequestViewOwner) {
                return replace(this.messaging.partnerRoot.persona);
            }
            if (this.threadNeedactionPreviewViewOwner) {
                return replace(this.threadNeedactionPreviewViewOwner.thread.correspondent.persona);
            }
            if (this.threadPreviewViewOwner) {
                return replace(this.threadPreviewViewOwner.thread.correspondent.persona);
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
