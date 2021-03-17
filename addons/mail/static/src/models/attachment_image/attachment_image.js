/** @odoo-module **/

import { registerNewModel } from '@mail/model/model_core';
import { attr, one2one } from '@mail/model/model_field';

function factory(dependencies) {

    class AttachmentImage extends dependencies['mail.model'] {

        /**
         * @override
         */
        _created() {
            // Bind necessary until OWL supports arrow function in handlers: https://github.com/odoo/owl/issues/876
            this.onClickUnlink = this.onClickUnlink.bind(this);
            this.onDeleteConfirmDialogClosed = this.onDeleteConfirmDialogClosed.bind(this);
            this.onClickImage = this.onClickImage.bind(this);
        }

        //----------------------------------------------------------------------
        // Public
        //----------------------------------------------------------------------

        /**
         * Open the attachment viewer when clicking on viewable attachment.
         *
         * @param {String} attachmentlistLocalId
         */
        onClickImage() {
            if (this.exists() && !this.attachment.isViewable) {
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
        _computeImageUrl() {
            if (this.attachment) {
                return `/web/image/${this.attachment.id}/${this.width}x${this.height}/`;
            }
        }

    }

    AttachmentImage.fields = {
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
        height: attr(),
        imageUrl: attr({
            compute: '_computeImageUrl',
        }),
        width: attr(),
    };

    AttachmentImage.modelName = 'mail.attachment_image';

    return AttachmentImage;
}

registerNewModel('mail.attachment_image', factory);
