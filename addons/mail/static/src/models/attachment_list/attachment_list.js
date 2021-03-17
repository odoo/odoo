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
                let width = 200;
                let height = 200;

                if (this.composer) {
                    width = 50;
                    height = 50;
                }

                if (this.thread) {
                    width = 160;
                    height = 160;
                }

                return {
                    attachmentList: link(this),
                    attachment: link(attachment),
                    height,
                    width,
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
         * Determines the attachments on this attachment list.
         */
        attachments: many2many('mail.attachment', {
            compute: '_computeAttachments',
            inverse: 'attachmentList',
        }),
        attachmentCards: one2many('mail.attachment_card', {
            compute: '_computeAttachmentCards',
        }),
        attachmentImages: one2many('mail.attachment_image', {
            compute: '_computeAttachmentImages',
        }),
        /**
         * Link with a composer to handle attachments.
         */
        composer: one2one('mail.composer', {
            inverse: 'attachmentList',
        }),
        /**
         * Link with a message to handle attachments.
         */
        message: one2one('mail.message', {
            inverse: 'attachmentList'
        }),
        /**
         * Link with a thread to handle attachments.
         */
        thread: one2one('mail.thread', {
            inverse: 'attachmentList'
        }),
        /**
         * States the attachment that are an image.
         */
        imageAttachments: one2many('mail.attachment', {
            compute: '_computeImageAttachments',
        }),
        /**
         * States the attachment that are not an image.
         */
        nonImageAttachments: one2many('mail.attachment', {
            compute: '_computeNonImageAttachments',
        }),
        /**
         * States the attachment that can be viewed inside the browser.
         */
        viewableAttachments: one2many('mail.attachment', {
            compute: '_computeViewableAttachments',
        }),
    };

    AttachmentList.modelName = 'mail.attachment_list';

    return AttachmentList;
}

registerNewModel('mail.attachment_list', factory);
