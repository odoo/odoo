/** @odoo-module **/

import { registerModel } from '@mail/model/model_core';
import { many, one } from '@mail/model/model_field';
import { clear, insertAndReplace, replace } from '@mail/model/model_field_command';

registerModel({
    name: 'AttachmentList',
    identifyingFields: [['composerViewOwner', 'messageViewOwner', 'attachmentBoxViewOwner']],
    recordMethods: {
        /**
         * Select the next attachment.
         */
        selectNextAttachment() {
            const index = this.attachments.findIndex(attachment => attachment === this.selectedAttachment);
            const nextIndex = index === this.attachments.length - 1 ? 0 : index + 1;
            this.update({ selectedAttachment: replace(this.attachments[nextIndex]) });
        },
        /**
         * Select the previous attachment.
         */
        selectPreviousAttachment() {
            const index = this.attachments.findIndex(attachment => attachment === this.selectedAttachment);
            const prevIndex = index === 0 ? this.attachments.length - 1 : index - 1;
            this.update({ selectedAttachment: replace(this.attachments[prevIndex]) });
        },
        _computeAttachmentImages() {
            return insertAndReplace(this.imageAttachments.map(attachment => {
                return {
                    attachment: replace(attachment),
                };
            }));
        },
        _computeAttachmentCards() {
            return insertAndReplace(this.nonImageAttachments.map(attachment => {
                return {
                    attachment: replace(attachment),
                };
            }));
        },
        /**
         * @returns {FieldCommand}
         */
        _computeAttachments() {
            if (this.messageViewOwner) {
                return replace(this.messageViewOwner.message.attachments);
            }
            if (this.attachmentBoxViewOwner) {
                return replace(this.attachmentBoxViewOwner.chatter.thread.allAttachments);
            }
            if (this.composerViewOwner && this.composerViewOwner.composer) {
                return replace(this.composerViewOwner.composer.attachments);
            }
            return clear();
        },
        /**
         * @returns {Attachment[]}
         */
        _computeImageAttachments() {
            return replace(this.attachments.filter(attachment => attachment.isImage));
        },
        /**
         * @returns {Attachment[]}
         */
        _computeNonImageAttachments() {
            return replace(this.attachments.filter(attachment => !attachment.isImage));
        },
        /**
         * @returns {Attachment[]}
         */
        _computeViewableAttachments() {
            return replace(this.attachments.filter(attachment => attachment.isViewable));
        },
    },
    fields: {
        /**
         * Link with a AttachmentBoxView to handle attachments.
         */
        attachmentBoxViewOwner: one('AttachmentBoxView', {
            inverse: 'attachmentList',
            readonly: true,
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
            inverse: 'attachmentList',
            readonly: true,
        }),
        /**
         * States the attachment that are an image.
         */
        imageAttachments: many('Attachment', {
            compute: '_computeImageAttachments',
        }),
        /**
         * Link with a message view to handle attachments.
         */
        messageViewOwner: one('MessageView', {
            inverse: 'attachmentList',
            readonly: true,
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
