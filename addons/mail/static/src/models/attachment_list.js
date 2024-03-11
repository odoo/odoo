/** @odoo-module **/

import { registerModel } from '@mail/model/model_core';
import { attr, many, one } from '@mail/model/model_field';
import { clear } from '@mail/model/model_field_command';

registerModel({
    name: 'AttachmentList',
    identifyingMode: 'xor',
    recordMethods: {
        /**
         * Select the next attachment.
         */
        selectNextAttachment() {
            const index = this.attachments.findIndex(attachment => attachment === this.selectedAttachment);
            const nextIndex = index === this.attachments.length - 1 ? 0 : index + 1;
            this.update({ selectedAttachment: this.attachments[nextIndex] });
        },
        /**
         * Select the previous attachment.
         */
        selectPreviousAttachment() {
            const index = this.attachments.findIndex(attachment => attachment === this.selectedAttachment);
            const prevIndex = index === 0 ? this.attachments.length - 1 : index - 1;
            this.update({ selectedAttachment: this.attachments[prevIndex] });
        },
    },
    fields: {
        /**
         * Link with a AttachmentBoxView to handle attachments.
         */
        attachmentBoxViewOwner: one('AttachmentBoxView', {
            identifying: true,
            inverse: 'attachmentList',
        }),
        /**
         * States the attachment cards that are displaying this nonImageAttachments.
         */
        attachmentCards: many('AttachmentCard', {
            compute() {
                return this.nonImageAttachments.map(attachment => ({ attachment }));
            },
            inverse: 'attachmentList',
        }),
        /**
         * States the attachment images that are displaying this imageAttachments.
         */
        attachmentImages: many('AttachmentImage', {
            compute() {
                return this.imageAttachments.map(attachment => ({ attachment }));
            },
            inverse: 'attachmentList',
        }),
        attachmentListViewDialog: one('Dialog', {
            inverse: 'attachmentListOwnerAsAttachmentView',
        }),
        /**
         * States the attachments to be displayed by this attachment list.
         */
        attachments: many('Attachment', {
            compute() {
                if (this.messageViewOwner) {
                    return this.messageViewOwner.message.attachments;
                }
                if (this.attachmentBoxViewOwner) {
                    return this.attachmentBoxViewOwner.chatter.thread.allAttachments;
                }
                if (this.composerViewOwner && this.composerViewOwner.composer) {
                    return this.composerViewOwner.composer.attachments;
                }
                return clear();
            },
            inverse: 'attachmentLists',
        }),
        /**
         * Link with a composer view to handle attachments.
         */
        composerViewOwner: one('ComposerView', {
            identifying: true,
            inverse: 'attachmentList',
        }),
        /**
         * States the attachment that are an image.
         */
        imageAttachments: many('Attachment', {
            compute() {
                return this.attachments.filter(attachment => attachment.isImage);
            },
        }),
        /**
         * Determines if we are in the Discuss view.
         */
        isInDiscuss: attr({
            compute() {
                return Boolean(
                    (this.messageViewOwner && this.messageViewOwner.isInDiscuss) ||
                    (this.composerViewOwner && this.composerViewOwner.isInDiscuss)
                );
            },
        }),
        /**
         * Determines if we are in the ChatWindow view.
         */
        isInChatWindow: attr({
            compute() {
                return Boolean(
                    (this.messageViewOwner && this.messageViewOwner.isInChatWindow) ||
                    (this.composerViewOwner && this.composerViewOwner.isInChatWindow)
                );
            },
        }),
        /**
         * Determines if we are in the Chatter view.
         */
        isInChatter: attr({
            compute() {
                return Boolean(
                    (this.messageViewOwner && this.messageViewOwner.isInChatter) ||
                    (this.composerViewOwner && this.composerViewOwner.isInChatter)
                );
            },
        }),
        /**
         * Determines if it comes from the current user.
         */
        isCurrentUserOrGuestAuthor: attr({
            compute() {
                return Boolean(
                    this.composerViewOwner ||
                    (this.messageViewOwner && this.messageViewOwner.message.isCurrentUserOrGuestAuthor)
                );
            },
        }),
        /**
         * Determines if we are in the ChatWindow view AND if the message is right aligned
         */
        isInChatWindowAndIsAlignedRight: attr({
            compute() {
                return Boolean(
                    this.isInChatWindow &&
                    this.isCurrentUserOrGuestAuthor
                );
            },
        }),
        /**
         * Determines if we are in the ChatWindow view AND if the message is left aligned
         */
        isInChatWindowAndIsAlignedLeft: attr({
            compute() {
                return Boolean(
                    this.isInChatWindow &&
                    !this.isCurrentUserOrGuestAuthor
                );
            },
        }),
        /**
         * Link with a message view to handle attachments.
         */
        messageViewOwner: one('MessageView', {
            identifying: true,
            inverse: 'attachmentList',
        }),
        /**
         * States the attachment that are not an image.
         */
        nonImageAttachments: many('Attachment', {
            compute() {
                return this.attachments.filter(attachment => !attachment.isImage);
            },
        }),
        selectedAttachment: one('Attachment'),
        /**
         * States the attachments that can be viewed inside the browser.
         */
        viewableAttachments: many('Attachment', {
            compute() {
                return this.attachments.filter(attachment => attachment.isViewable);
            },
        }),
    },
});
