/** @odoo-module **/

import { registerModel } from '@mail/model/model_core';
import { attr, one } from '@mail/model/model_field';
import { clear } from '@mail/model/model_field_command';
import { isEventHandled, markEventHandled } from '@mail/utils/utils';

registerModel({
    name: 'AttachmentImageView',
    recordMethods: {
        /**
         * Called when clicking on download icon.
         *
         * @param {MouseEvent} ev
         */
        onClickDownload(ev) {
            markEventHandled(ev, 'AttachmentImageView.onClickDownload');
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
            if (isEventHandled(ev, 'AttachmentImageView.onClickDownload')) {
                return;
            }
            if (isEventHandled(ev, 'AttachmentImageView.onClickUnlink')) {
                return;
            }
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
            markEventHandled(ev, 'AttachmentImageView.onClickUnlink');
            if (!this.exists()) {
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
         * Determines the attachment of this attachment image..
         */
        attachment: one('Attachment', {
            identifying: true,
        }),
        attachmentDeleteConfirmDialog: one('Dialog', {
            inverse: 'attachmentImageViewOwnerAsAttachmentDeleteConfirm',
        }),
        /**
         * States the attachmentListView displaying this attachment image.
         */
        attachmentListView: one('AttachmentListView', {
            identifying: true,
            inverse: 'attachmentImageViews',
        }),
        /**
         * Determines whether `this` should display a download button.
         */
        hasDownloadButton: attr({
            compute() {
                if (!this.attachment || !this.attachmentListView) {
                    return clear();
                }
                return !this.attachmentListView.composerViewOwner && !this.attachment.isUploading;
            },
            default: false,
        }),
        /**
         * Determines the max height of this attachment image in px.
         */
        height: attr({
            compute() {
                if (!this.attachmentListView) {
                    return clear();
                }
                if (this.attachmentListView.composerViewOwner) {
                    return 50;
                }
                if (this.attachmentListView.attachmentBoxViewOwner) {
                    return 160;
                }
                if (this.attachmentListView.messageViewOwner) {
                    return 300;
                }
            },
            required: true,
        }),
        imageUrl: attr({
            compute() {
                if (!this.attachment) {
                    return;
                }
                if (!this.attachment.accessToken && this.attachment.originThread && this.attachment.originThread.model === 'mail.channel') {
                    return `/mail/channel/${this.attachment.originThread.id}/image/${this.attachment.id}/${this.width}x${this.height}`;
                }
                const accessToken = this.attachment.accessToken ? `?access_token=${this.attachment.accessToken}` : '';
                return `/web/image/${this.attachment.id}/${this.width}x${this.height}${accessToken}`;
            },
        }),
        /**
         * Determines the max width of this attachment image in px.
         */
        width: attr({
            /**
             * Returns an arbitrary high value, this is effectively a max-width and
             * the height should be more constrained.
             */
            compute() {
                return 1920;
            },
            required: true,
        }),
    },
});
