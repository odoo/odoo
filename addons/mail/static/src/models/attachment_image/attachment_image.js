/** @odoo-module **/

import { registerNewModel } from '@mail/model/model_core';
import { attr, many2one } from '@mail/model/model_field';

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
         * Synchronize the `hasDeleteConfirmDialog` when the dialog is closed.
         */
        onDeleteConfirmDialogClosed() {
            if (!this.exists()) {
                return;
            }
            this.update({ hasDeleteConfirmDialog: false });
        }

        //----------------------------------------------------------------------
        // Private
        //----------------------------------------------------------------------

        /**
         * @private
         * @returns {number}
         */
        _computeHeight() {
            return this.width;
        }

        /**
         * @private
         * @returns {string}
         */
        _computeImageUrl() {
            if (!this.attachment) {
                return;
            }
            if (!this.attachment.accessToken && this.attachment.originThread && this.attachment.originThread.model === 'mail.channel') {
                return `/mail/channel/${this.attachment.originThread.id}/image/${this.attachment.id}/${this.width}x${this.height}`;
            }
            const accessToken = this.attachment.accessToken ? `?access_token=${this.attachment.accessToken}` : '';
            return `/web/image/${this.attachment.id}/${this.width}x${this.height}${accessToken}`;
        }

        /**
         * @private
         * @returns {number}
         */
        _computeWidth() {
            if (!this.attachmentList) {
                return;
            }
            if (this.attachmentList.composer) {
                return 50;
            }
            if (this.attachmentList.thread) {
                return 160;
            }
            if (this.attachmentList.message) {
                return 300;
            }
        }
    }

    AttachmentImage.fields = {
        /**
         * Determines the attachment of this card.
         */
        attachment: many2one('mail.attachment', {
            inverse: 'attachmentImages',
            required: true,
        }),
        /**
         * Determines the attachmentList for this card.
         */
        attachmentList: many2one('mail.attachment_list', {
            required: true,
        }),
        /**
         * States the OWL component of this attachment image.
         */
        component: attr(),
        /**
         * Determines the status of the delete confirm dialog (open/closed).
         */
        hasDeleteConfirmDialog: attr({
            default: false,
        }),
        /**
         * Determines the max height of this attachment image in px.
         */
        height: attr({
            compute: '_computeHeight',
            required: true,
        }),
        imageUrl: attr({
            compute: '_computeImageUrl',
        }),
        /**
         * Determines the max width of this attachment image in px.
         */
        width: attr({
            compute: '_computeWidth',
            required: true,
        }),
    };

    AttachmentImage.modelName = 'mail.attachment_image';

    return AttachmentImage;
}

registerNewModel('mail.attachment_image', factory);
