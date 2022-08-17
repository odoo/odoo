/** @odoo-module **/

import { registerModel } from '@mail/model/model_core';
import { attr, many, one } from '@mail/model/model_field';
import { clear, insertAndReplace } from '@mail/model/model_field_command';

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
        _computeAttachmentImages() {
            return insertAndReplace(this.imageAttachments.map(attachment => {
                return {
                    attachment,
                };
            }));
        },
        _computeAttachmentCards() {
            return insertAndReplace(this.nonImageAttachments.map(attachment => {
                return {
                    attachment,
                };
            }));
        },
        /**
         * @returns {FieldCommand}
         */
        _computeAttachments() {
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
        /**
         * @returns {Attachment[]}
         */
        _computeImageAttachments() {
            return this.attachments.filter(attachment => attachment.isImage);
        },
        /**
         * @returns {Attachment[]}
         */
        _computeNonImageAttachments() {
            return this.attachments.filter(attachment => !attachment.isImage);
        },
        /**
         * @returns {Attachment[]}
         */
        _computeViewableAttachments() {
            return this.attachments.filter(attachment => attachment.isViewable);
        },
        /**
         * @private
         * @returns {boolean}
         */
        _computeIsInDiscuss() {
            return Boolean(
                (this.messageViewOwner && this.messageViewOwner.isInDiscuss) ||
                (this.composerViewOwner && this.composerViewOwner.isInDiscuss)
            );
        },
        /**
         * @private
         * @returns {boolean}
         */
        _computeIsInChatWindow() {
            return Boolean(
                (this.messageViewOwner && this.messageViewOwner.isInChatWindow) ||
                (this.composerViewOwner && this.composerViewOwner.isInChatWindow)
            );
        },
        /**
         * @private
         * @returns {boolean}
         */
        _computeIsInChatter() {
            return Boolean(
                (this.messageViewOwner && this.messageViewOwner.isInChatter) ||
                (this.composerViewOwner && this.composerViewOwner.isInChatter)
            );
        },
        /**
         * @private
         * @returns {boolean}
         */
        _computeIsCurrentUserOrGuestAuthor() {
            return Boolean(
                this.composerViewOwner ||
                (this.messageViewOwner && this.messageViewOwner.message.isCurrentUserOrGuestAuthor)
            );
        },
        /**
         * @private
         * @returns {boolean}
         */
         _computeIsInChatWindowAndIsAlignedRight() {
            return Boolean(
                this.isInChatWindow &&
                this.isCurrentUserOrGuestAuthor
            );
        },
        /**
         * @private
         * @returns {boolean}
         */
         _computeIsInChatWindowAndIsAlignedLeft() {
            return Boolean(
                this.isInChatWindow &&
                !this.isCurrentUserOrGuestAuthor
            );
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
            compute: '_computeAttachmentCards',
            inverse: 'attachmentList',
            isCausal: true,
        }),
        /**
         * States the attachment images that are displaying this imageAttachments.
         */
        attachmentImages: many('AttachmentImage', {
            compute: '_computeAttachmentImages',
            inverse: 'attachmentList',
            isCausal: true,
        }),
        attachmentListViewDialog: one('Dialog', {
            inverse: 'attachmentListOwnerAsAttachmentView',
            isCausal: true,
        }),
        /**
         * States the attachments to be displayed by this attachment list.
         */
        attachments: many('Attachment', {
            compute: '_computeAttachments',
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
            compute: '_computeImageAttachments',
        }),
        /**
         * Determines if we are in the Discuss view.
         */
        isInDiscuss: attr({
            compute: '_computeIsInDiscuss',
        }),
        /**
         * Determines if we are in the ChatWindow view.
         */
        isInChatWindow: attr({
            compute: '_computeIsInChatWindow',
        }),
        /**
         * Determines if we are in the Chatter view.
         */
        isInChatter: attr({
            compute: '_computeIsInChatter',
        }),
        /**
         * Determines if it comes from the current user.
         */
        isCurrentUserOrGuestAuthor: attr({
            compute: '_computeIsCurrentUserOrGuestAuthor',
        }),
        /**
         * Determines if we are in the ChatWindow view AND if the message is right aligned
         */
        isInChatWindowAndIsAlignedRight: attr({
            compute: '_computeIsInChatWindowAndIsAlignedRight',
        }),
        /**
         * Determines if we are in the ChatWindow view AND if the message is left aligned
         */
        isInChatWindowAndIsAlignedLeft: attr({
            compute: '_computeIsInChatWindowAndIsAlignedLeft',
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
            compute: '_computeNonImageAttachments',
        }),
        selectedAttachment: one('Attachment'),
        /**
         * States the attachments that can be viewed inside the browser.
         */
        viewableAttachments: many('Attachment', {
            compute: '_computeViewableAttachments',
        }),
    },
});
