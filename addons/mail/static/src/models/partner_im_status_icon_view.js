/** @odoo-module **/

import { one } from '@mail/model/model_field';
import { registerModel } from '@mail/model/model_core';
import { clear, replace } from '@mail/model/model_field_command';

registerModel({
    name: 'PartnerImStatusIconView',
    identifyingFields: [[
        'channelInvitationFormSelectablePartnerViewOwner',
        'channelMemberViewOwner',
        'composerSuggestionViewOwner',
        'messageViewOwner',
        'notificationRequestViewOwner',
        'threadNeedactionPreviewViewOwner',
        'threadPreviewViewOwner',
    ]],
    recordMethods: {
        /**
         * @private
         * @returns {FieldCommand}
         */
        _computePartner() {
            if (this.channelInvitationFormSelectablePartnerViewOwner) {
                return replace(this.channelInvitationFormSelectablePartnerViewOwner.partner);
            }
            if (this.channelMemberViewOwner) {
                return replace(this.channelMemberViewOwner.channelMember.partner);
            }
            if (this.composerSuggestionViewOwner) {
                return replace(this.composerSuggestionViewOwner.partner);
            }
            if (this.messageViewOwner) {
                return replace(this.messageViewOwner.message.author);
            }
            if (this.notificationRequestViewOwner) {
                return replace(this.messaging.partnerRoot);
            }
            if (this.threadNeedactionPreviewViewOwner) {
                return replace(this.threadNeedactionPreviewViewOwner.thread.correspondent);
            }
            if (this.threadPreviewViewOwner) {
                return replace(this.threadPreviewViewOwner.thread.correspondent);
            }
            return clear();
        },
    },
    fields: {
        channelInvitationFormSelectablePartnerViewOwner: one('ChannelInvitationFormSelectablePartnerView', {
            inverse: 'partnerImStatusIconView',
            readonly: true,
        }),
        channelMemberViewOwner: one('ChannelMemberView', {
            inverse: 'partnerImStatusIconView',
            readonly: true,
        }),
        composerSuggestionViewOwner: one('ComposerSuggestion', {
            inverse: 'partnerImStatusIconView',
            readonly: true,
        }),
        messageViewOwner: one('MessageView', {
            inverse: 'partnerImStatusIconView',
            readonly: true,
        }),
        notificationRequestViewOwner: one('NotificationRequestView', {
            inverse: 'partnerImStatusIconView',
            readonly: true,
        }),
        threadNeedactionPreviewViewOwner: one('ThreadNeedactionPreviewView', {
            inverse: 'partnerImStatusIconView',
            readonly: true,
        }),
        threadPreviewViewOwner: one('ThreadPreviewView', {
            inverse: 'partnerImStatusIconView',
            readonly: true,
        }),
        partner: one('Partner', {
            compute: '_computePartner',
            readonly: true,
            required: true,
        }),
    },
});
