/** @odoo-module **/

import { registerNewModel } from '@mail/model/model_core';
import { many2many, one2many, one2one } from '@mail/model/model_field';
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
            if (this.thread) {
                return replace(this.thread.allAttachments);
            }
            if (this.composer) {
                return replace(this.composer.attachments);
            }
            return clear();
        }

        _computeAttachmentImages() {
            return insertAndReplace(this.imageAttachments.map(attachment => {
                return {
                    attachmentList: link(this),
                    attachment: link(attachment),
                };
            }));
        }

        _computeAttachmentCards() {
            return insertAndReplace(this.nonImageAttachments.map(attachment => {
                return {
                    attachmentList: link(this),
                    attachment: link(attachment),
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
         * @returns {mail.attachment[]}
         */
        _computeNonImageAttachments() {
            return replace(this.attachments.filter(attachment => !attachment.isImage));
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
            inverse: 'attachmentList',
        }),
        /**
         * States the attachment cards that are displaying this nonImageAttachments.
         */
        attachmentCards: one2many('mail.attachment_card', {
            compute: '_computeAttachmentCards',
            isCausal: true,
        }),
        /**
         * States the attachment images that are displaying this imageAttachments.
         */
        attachmentImages: one2many('mail.attachment_image', {
            compute: '_computeAttachmentImages',
            isCausal: true,
        }),
        /**
         * Link with a composer to handle attachments.
         */
        composer: one2one('mail.composer', {
            inverse: 'attachmentList',
        }),
        /**
         * States the attachment that are an image.
         */
        imageAttachments: one2many('mail.attachment', {
            compute: '_computeImageAttachments',
        }),
        /**
         * Link with a message to handle attachments.
         */
        message: one2one('mail.message', {
            inverse: 'attachmentList'
        }),
        /**
         * States the attachment that are not an image.
         */
        nonImageAttachments: one2many('mail.attachment', {
            compute: '_computeNonImageAttachments',
        }),
        /**
         * Link with a thread to handle attachments.
         */
        thread: one2one('mail.thread', {
            inverse: 'attachmentList'
        }),
        /**
         * States the attachments that can be viewed inside the browser.
         */
        viewableAttachments: one2many('mail.attachment', {
            compute: '_computeViewableAttachments',
        }),
    };

    AttachmentList.modelName = 'mail.attachment_list';

    return AttachmentList;
}

registerNewModel('mail.attachment_list', factory);
