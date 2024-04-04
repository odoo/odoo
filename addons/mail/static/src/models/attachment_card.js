/** @odoo-module **/

import { registerModel } from '@mail/model/model_core';
import { attr, one } from '@mail/model/model_field';

registerModel({
    name: 'AttachmentCard',
    recordMethods: {
        /**
         * Opens the attachment viewer when clicking on viewable attachment.
         */
        onClickImage() {
            if (!this.attachment || !this.attachment.isViewable) {
                return;
            }
            this.attachmentList.update({
                attachmentListViewDialog: {},
                selectedAttachment: this.attachment,
            });
        },
        /**
         * Handles the click on delete attachment and open the confirm dialog.
         *
         * @param {MouseEvent} ev
         */
        onClickUnlink(ev) {
            ev.stopPropagation(); // prevents from opening viewer
            if (!this.attachment) {
                return;
            }
            if (this.attachmentList.composerViewOwner) {
                this.attachment.remove();
            } else {
                this.update({ attachmentDeleteConfirmDialog: {} });
            }
        },
    },
    fields: {
        /**
         * Determines the attachment of this card.
         */
        attachment: one('Attachment', {
            identifying: true,
        }),
        attachmentDeleteConfirmDialog: one('Dialog', {
            inverse: 'attachmentCardOwnerAsAttachmentDeleteConfirm',
        }),
        /**
         * States the attachmentList displaying this card.
         */
        attachmentList: one('AttachmentList', {
            identifying: true,
            inverse: 'attachmentCards',
        }),
        hasMultipleActions: attr({
            compute() {
                return this.attachment.isDeletable && !this.attachmentList.composerViewOwner;
            },
        }),
    },
});
