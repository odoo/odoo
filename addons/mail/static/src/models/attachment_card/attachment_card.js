/** @odoo-module **/

import { registerNewModel } from '@mail/model/model_core';
import { attr, many2one } from '@mail/model/model_field';

function factory(dependencies) {

    class AttachmentCard extends dependencies['mail.model'] {

        /**
         * @override
         */
        _created() {
            // Bind necessary until OWL supports arrow function in handlers: https://github.com/odoo/owl/issues/876
            this.onClickUnlink = this.onClickUnlink.bind(this);
            this.onClickImage = this.onClickImage.bind(this);
            this.onDeleteConfirmDialogClosed = this.onDeleteConfirmDialogClosed.bind(this);
        }

        //----------------------------------------------------------------------
        // Public
        //----------------------------------------------------------------------

        /**
         * Opens the attachment viewer when clicking on viewable attachment.
         *
         * @param {String} attachmentlistLocalId
         */
        onClickImage() {
            if (!this.attachment || !this.attachment.isViewable) {
                return;
            }
            this.messaging.models['mail.attachment'].view({
                attachment: this.attachment,
                attachments: this.attachmentList.viewableAttachments,
            });
        }

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
            if (this.attachment.isLinkedToComposer) {
                this.component.trigger('o-attachment-removed', { attachmentLocalId: this.attachment.localId });
                this.attachment.remove();
            } else {
                this.update({ hasDeleteConfirmDialog: true });
            }
        }

        /**
         * Synchronizes the `hasDeleteConfirmDialog` when the dialog is closed.
         */
        onDeleteConfirmDialogClosed() {
            if (!this.exists()) {
                return;
            }
            this.update({ hasDeleteConfirmDialog: false });
        }

    }

    AttachmentCard.fields = {
        /**
         * Determines the attachment of this card.
         */
        attachment: many2one('mail.attachment', {
            inverse: 'attachmentCards',
            required: true,
        }),
        /**
         * Determines the attachmentList for this card.
         */
        attachmentList: many2one('mail.attachment_list', {
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
    };

    AttachmentCard.modelName = 'mail.attachment_card';

    return AttachmentCard;
}

registerNewModel('mail.attachment_card', factory);
