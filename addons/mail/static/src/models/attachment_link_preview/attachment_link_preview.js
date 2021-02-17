/** @odoo-module **/

import { registerNewModel } from '@mail/model/model_core';
import { attr, one2one } from '@mail/model/model_field';

function factory(dependencies) {

    class AttachmentlinkPreview extends dependencies['mail.model'] {

        /**
         * @override
         */
        _created() {
            // Bind necessary until OWL supports arrow function in handlers: https://github.com/odoo/owl/issues/876
            this.onClickUnlink = this.onClickUnlink.bind(this);
            this.onDeleteConfirmDialogClosed = this.onDeleteConfirmDialogClosed.bind(this);
        }

        //----------------------------------------------------------------------
        // Public
        //----------------------------------------------------------------------

        /**
         * Handles the click on delete attachment and open the confirm dialog.
         *
         * @param {MouseEvent} ev
         */
        onClickUnlink(ev) {
            ev.stopPropagation();
            if (this.attachment) {
                if (this.attachment.isLinkedToComposer) {
                    this.component.trigger('o-attachment-removed', { attachmentLocalId: this.attachment.localId });
                    this.attachment.remove();
                } else {
                    this.update({ hasDeleteConfirmDialog: true });
                }
            }
        }

        /**
         * Synchronize the `hasDeleteConfirmDialog` when the dialog is closed.
         */
        onDeleteConfirmDialogClosed() {
            this.update({
                hasDeleteConfirmDialog: false,
            });
        }

        //----------------------------------------------------------------------
        // Private
        //----------------------------------------------------------------------

    }

    AttachmentlinkPreview.fields = {
        /**
         * Determines the attachment of this card.
         */
        attachment: one2one('mail.attachment'),
        /**
         * Determines the attachmentList for this card.
         */
        attachmentList: one2one('mail.attachment_list'),
        /**
         * States the OWL component of this attachment image.
         */
        component: attr(),
        /**
         * States the status of the delete confirm dialog (open/closed).
         */
        hasDeleteConfirmDialog: attr({
            default: false,
        }),
    };

    AttachmentlinkPreview.modelName = 'mail.attachment_link_preview';

    return AttachmentlinkPreview;
}

registerNewModel('mail.attachment_link_preview', factory);
