/** @odoo-module **/

import { registerModel } from '@mail/model/model_core';
import { many2many, many2one, one2many, one2one } from '@mail/model/model_field';
import { clear, insertAndReplace, replace } from '@mail/model/model_field_command';

registerModel({
    name: 'AttachmentList',
    identifyingFields: [['composerView', 'messageView', 'chatter']],
    recordMethods: {
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
         * @returns {Attachment[]}
         */
        _computeAttachments() {
            if (this.message) {
                return replace(this.message.attachments);
            }
            if (this.chatter && this.chatter.thread) {
                return replace(this.chatter.thread.allAttachments);
            }
            if (this.composerView && this.composerView.composer) {
                return replace(this.composerView.composer.attachments);
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
         * States the attachments to be displayed by this attachment list.
         */
        attachments: many2many('Attachment', {
            compute: '_computeAttachments',
            inverse: 'attachmentLists',
        }),
        /**
         * States the attachment cards that are displaying this nonImageAttachments.
         */
        attachmentCards: one2many('AttachmentCard', {
            compute: '_computeAttachmentCards',
            inverse: 'attachmentList',
            isCausal: true,
        }),
        /**
         * States the attachment images that are displaying this imageAttachments.
         */
        attachmentImages: one2many('AttachmentImage', {
            compute: '_computeAttachmentImages',
            inverse: 'attachmentList',
            isCausal: true,
        }),
        /**
         * Determines the attachment viewers displaying this attachment list (if any).
         */
        attachmentViewers: one2many('AttachmentViewer', {
            inverse: 'attachmentList',
            isCausal: true,
        }),
        /**
         * Link with a chatter to handle attachments.
         */
        chatter: one2one('Chatter', {
            inverse: 'attachmentList',
            readonly: true,
        }),
        /**
         * Link with a composer view to handle attachments.
         */
        composerView: one2one('ComposerView', {
            inverse: 'attachmentList',
            readonly: true,
        }),
        /**
         * States the attachment that are an image.
         */
        imageAttachments: many2many('Attachment', {
            compute: '_computeImageAttachments',
        }),
        message: many2one('Message', {
            related: 'messageView.message'
        }),
        /**
         * Link with a message view to handle attachments.
         */
        messageView: one2one('MessageView', {
            inverse: 'attachmentList',
            readonly: true,
        }),
        /**
         * States the attachment that are not an image.
         */
        nonImageAttachments: many2many('Attachment', {
            compute: '_computeNonImageAttachments',
        }),
        /**
         * States the attachments that can be viewed inside the browser.
         */
        viewableAttachments: many2many('Attachment', {
            compute: '_computeViewableAttachments',
        }),
    },
});
