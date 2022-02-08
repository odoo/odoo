/** @odoo-module **/

import { registerModel } from '@mail/model/model_core';
import { attr, one } from '@mail/model/model_field';
import { insertAndReplace, replace } from '@mail/model/model_field_command';

registerModel({
    name: 'AttachmentCard',
    identifyingFields: ['attachmentList', 'attachment'],
    recordMethods: {
        /**
         * Opens the attachment viewer when clicking on viewable attachment.
         */
        onClickImage() {
            if (!this.attachment || !this.attachment.isViewable) {
                return;
            }
            this.attachmentList.update({
                attachmentListViewDialog: insertAndReplace(),
                selectedAttachment: replace(this.attachment),
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
                this.component.trigger('o-attachment-removed', { attachmentLocalId: this.attachment.localId });
                this.attachment.remove();
            } else {
                this.update({ attachmentDeleteConfirmDialog: insertAndReplace() });
            }
        },
    },
    fields: {
        /**
         * Determines the attachment of this card.
         */
        attachment: one('Attachment', {
            readonly: true,
            required: true,
        }),
        attachmentDeleteConfirmDialog: one('Dialog', {
            inverse: 'attachmentCardOwnerAsAttachmentDeleteConfirm',
            isCausal: true,
        }),
        /**
         * States the attachmentList displaying this card.
         */
        attachmentList: one('AttachmentList', {
            inverse: 'attachmentCards',
            readonly: true,
            required: true,
        }),
        /**
         * States the OWL component of this attachment card.
         */
        component: attr(),
    },
});
