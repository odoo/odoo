/** @odoo-module **/

import { registerModel } from '@mail/model/model_core';
import { attr, one } from '@mail/model/model_field';

registerModel({
    name: 'AttachmentCardView',
    recordMethods: {
        /**
         * Opens the attachment viewer when clicking on viewable attachment.
         */
        onClickImage() {
            if (!this.attachment || !this.attachment.isViewable) {
                return;
            }
            this.attachmentListView.update({
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
            if (this.attachmentListView.composerViewOwner) {
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
            inverse: 'attachmentCardViewOwnerAsAttachmentDeleteConfirm',
        }),
        /**
         * States the attachmentListView displaying this card.
         */
        attachmentListView: one('AttachmentListView', {
            identifying: true,
            inverse: 'attachmentCardViews',
        }),
        hasMultipleActions: attr({
            compute() {
                return this.attachment.isDeletable && !this.attachmentListView.composerViewOwner;
            },
        }),
    },
});
