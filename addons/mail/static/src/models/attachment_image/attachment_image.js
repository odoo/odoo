/** @odoo-module **/

import { registerModel } from '@mail/model/model_core';
import { attr, many2one } from '@mail/model/model_field';
import { clear, insert, insertAndReplace, replace } from '@mail/model/model_field_command';

registerModel({
    name: 'AttachmentImage',
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
         * Synchronize the `hasDeleteConfirmDialog` when the dialog is closed.
         */
        onDeleteConfirmDialogClosed() {
            if (!this.exists()) {
                return;
            }
            this.update({ hasDeleteConfirmDialog: false });
        },
        /**
         * @private
         * @returns {number}
         */
        _computeHeight() {
            if (!this.attachmentList) {
                return clear();
            }
            if (this.attachmentList.composerView) {
                return 50;
            }
            if (this.attachmentList.chatter) {
                return 160;
            }
            if (this.attachmentList.message) {
                return 300;
            }
        },
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
        },
        /**
         * Returns an arbitrary high value, this is effectively a max-width and
         * the height should be more constrained.
         *
         * @private
         * @returns {number}
         */
        _computeWidth() {
            return 1920;
        },
    },
    fields: {
        /**
         * Determines the attachment of this attachment image..
         */
        attachment: many2one('Attachment', {
            readonly: true,
            required: true,
        }),
        /**
         * States the attachmentList displaying this attachment image.
         */
        attachmentList: many2one('AttachmentList', {
            inverse: 'attachmentImages',
            readonly: true,
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
    },
});
