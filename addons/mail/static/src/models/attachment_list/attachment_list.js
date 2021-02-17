/** @odoo-module **/

import { registerNewModel } from '@mail/model/model_core';
import { many2many, many2one, one2many, one2one } from '@mail/model/model_field';
import { clear, insertAndReplace, link, replace } from '@mail/model/model_field_command';

function factory(dependencies) {

    class AttachmentList extends dependencies['mail.model'] {

        //----------------------------------------------------------------------
        // Private
        //----------------------------------------------------------------------

        /**
         * @returns {mail.attachment[]}
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
        }

        /**
         * @private
         * @returns FieldCommand
         */
        _computeAttachmentImagesView() {
            return insertAndReplace(this.imageAttachments.map(attachment => {
                return {
                    attachment: replace(attachment),
                };
            }));
        }

        /**
         * @private
         * @returns FieldCommand
         */
        _computeAttachmentLinkPreviewsView() {
            return insertAndReplace(this.linkPreviewAttachments.map(attachment => {
                return {
                    attachment: link(attachment),
                };
            }));
        }

        /**
         * @private
         * @returns FieldCommand
         */
        _computeAttachmentCardsView() {
            return insertAndReplace(this.nonImageAttachments.map(attachment => {
                return {
                    attachment: replace(attachment),
                };
            }));
        }

        /**
         * @returns {mail.attachment[]}
         */
        _computeImageAttachments() {
            return replace(this.attachments.filter(attachment => attachment.isImage));
        }

        /**
         * @returns FieldCommand
         */
        _computeLinkPreviewAttachments() {
            return replace(this.attachments.filter(attachment => attachment.isLinkPreview));
        }

        /**
         * @returns {mail.attachment[]}
         */
        _computeNonImageAttachments() {
            return replace(this.attachments.filter(attachment => !attachment.isImage && !attachment.isLinkPreview));
        }

        /**
         * @returns {mail.attachment[]}
         */
        _computeViewableAttachments() {
            return replace(this.attachments.filter(attachment => attachment.isViewable));
        }

    }

    AttachmentList.fields = {
        /**
         * States the attachments to be displayed by this attachment list.
         */
        attachments: many2many('mail.attachment', {
            compute: '_computeAttachments',
            inverse: 'attachmentLists',
        }),
        /**
         * States the attachment cards that are displaying this nonImageAttachments.
         */
        attachmentCardsView: one2many('mail.attachment_card_view', {
            compute: '_computeAttachmentCardsView',
            inverse: 'attachmentList',
            isCausal: true,
        }),
        /**
         * States the attachment images that are displaying this imageAttachments.
         */
        attachmentImagesView: one2many('mail.attachment_image_view', {
            compute: '_computeAttachmentImagesView',
            inverse: 'attachmentList',
            isCausal: true,
        }),
        attachmentLinkPreviewsView: one2many('mail.attachment_link_preview_view', {
            compute: '_computeAttachmentLinkPreviewsView',
            inverse: 'attachmentList',
            isCausal: true,
        }),
        /**
         * Determines the attachment viewers displaying this attachment list (if any).
         */
        attachmentViewer: one2many('mail.attachment_viewer', {
            inverse: 'attachmentList',
            isCausal: true,
        }),
        /**
         * Link with a chatter to handle attachments.
         */
        chatter: one2one('mail.chatter', {
            inverse: 'attachmentList',
            readonly: true,
        }),
        /**
         * Link with a composer view to handle attachments.
         */
        composerView: one2one('mail.composer_view', {
            inverse: 'attachmentList',
            readonly: true,
        }),
        /**
         * States the attachment that are an image.
         */
        imageAttachments: many2many('mail.attachment', {
            compute: '_computeImageAttachments',
        }),
        /**
         * States the attachment that are link previews.
         */
        linkPreviewAttachments: many2many('mail.attachment', {
            compute: '_computeLinkPreviewAttachments',
        }),
        message: many2one('mail.message', {
            related: 'messageView.message'
        }),
        /**
         * Link with a message view to handle attachments.
         */
        messageView: one2one('mail.message_view', {
            inverse: 'attachmentList',
            readonly: true,
        }),
        /**
         * States the attachment that are not an image.
         */
        nonImageAttachments: many2many('mail.attachment', {
            compute: '_computeNonImageAttachments',
        }),
        /**
         * States the attachments that can be viewed inside the browser.
         */
        viewableAttachments: many2many('mail.attachment', {
            compute: '_computeViewableAttachments',
        }),
    };
    AttachmentList.identifyingFields = [['composerView', 'messageView', 'chatter']];
    AttachmentList.modelName = 'mail.attachment_list';

    return AttachmentList;
}

registerNewModel('mail.attachment_list', factory);
