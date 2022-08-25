/** @odoo-module **/

import { registerModel } from '@mail/model/model_core';
import { attr, one } from '@mail/model/model_field';
import { clear } from '@mail/model/model_field_command';
import { isEventHandled, markEventHandled } from '@mail/utils/utils';

registerModel({
    name: 'AttachmentImage',
    recordMethods: {
        /**
         * Called when clicking on download icon.
         *
         * @param {MouseEvent} ev
         */
        onClickDownload(ev) {
            markEventHandled(ev, 'AttachmentImage.onClickDownload');
            if (!this.exists()) {
                return;
            }
            this.attachment.download();
        },
        /**
         * Opens the attachment viewer when clicking on viewable attachment.
         *
         * @param {MouseEvent} ev
         */
        onClickImage(ev) {
            if (isEventHandled(ev, 'AttachmentImage.onClickDownload')) {
                return;
            }
            if (isEventHandled(ev, 'AttachmentImage.onClickUnlink')) {
                return;
            }
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
            markEventHandled(ev, 'AttachmentImage.onClickUnlink');
            if (!this.exists()) {
                return;
            }
            if (this.attachmentList.composerViewOwner) {
                this.attachment.remove();
            } else {
                this.update({ attachmentDeleteConfirmDialog: {} });
            }
        },
        /**
         * @private
         * @returns {boolean}
         */
        _computeHasDownloadButton() {
            if (!this.attachment || !this.attachmentList) {
                return clear();
            }
            return !this.attachmentList.composerViewOwner && !this.attachment.isUploading;
        },
        /**
         * @private
         * @returns {number}
         */
        _computeHeight() {
            if (!this.attachmentList) {
                return clear();
            }
            if (this.attachmentList.composerViewOwner) {
                return 50;
            }
            if (this.attachmentList.attachmentBoxViewOwner) {
                return 160;
            }
            if (this.attachmentList.messageViewOwner) {
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
        attachment: one('Attachment', {
            identifying: true,
        }),
        attachmentDeleteConfirmDialog: one('Dialog', {
            inverse: 'attachmentImageOwnerAsAttachmentDeleteConfirm',
            isCausal: true,
        }),
        /**
         * States the attachmentList displaying this attachment image.
         */
        attachmentList: one('AttachmentList', {
            identifying: true,
            inverse: 'attachmentImages',
        }),
        /**
         * Determines whether `this` should display a download button.
         */
        hasDownloadButton: attr({
            compute: '_computeHasDownloadButton',
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
