/** @odoo-module **/

import { registerModel } from '@mail/model/model_core';
import { attr, one } from '@mail/model/model_field';
import { insert, insertAndReplace, replace } from '@mail/model/model_field_command';

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
            this.messaging.dialogManager.update({
                dialogs: insert({
                    attachmentViewer: insertAndReplace({
                        attachment: replace(this.attachment),
                        attachmentList: replace(this.attachmentList),
                    }),
                }),
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
            if (this.attachmentList.composerView) {
                this.component.trigger('o-attachment-removed', { attachmentLocalId: this.attachment.localId });
                this.attachment.remove();
            } else {
                this.update({ hasDeleteConfirmDialog: true });
            }
        },
        /**
         * Synchronizes the `hasDeleteConfirmDialog` when the dialog is closed.
         */
        onDeleteConfirmDialogClosed() {
            if (!this.exists()) {
                return;
            }
            this.update({ hasDeleteConfirmDialog: false });
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
        /**
         * Determines the status of the delete confirm dialog (open/closed).
         */
        hasDeleteConfirmDialog: attr({
            default: false,
        }),
    },
});
