/** @odoo-module **/

import { attr, clear, one, Model } from "@mail/model";
import { isEventHandled, markEventHandled } from "@mail/utils/utils";

Model({
    name: "AttachmentImage",
    template: "mail.AttachmentImage",
    recordMethods: {
        /**
         * Called when clicking on download icon.
         *
         * @param {MouseEvent} ev
         */
        onClickDownload(ev) {
            markEventHandled(ev, "AttachmentImage.onClickDownload");
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
            if (isEventHandled(ev, "AttachmentImage.onClickDownload")) {
                return;
            }
            if (isEventHandled(ev, "AttachmentImage.onClickUnlink")) {
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
            markEventHandled(ev, "AttachmentImage.onClickUnlink");
            if (!this.exists()) {
                return;
            }
            if (this.attachmentList.composerViewOwner) {
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
        attachment: one("Attachment", { identifying: true }),
        attachmentDeleteConfirmDialog: one("Dialog", {
            inverse: "attachmentImageOwnerAsAttachmentDeleteConfirm",
        }),
        /**
         * States the attachmentList displaying this attachment image.
         */
        attachmentList: one("AttachmentList", { identifying: true, inverse: "attachmentImages" }),
        /**
         * Determines whether `this` should display a download button.
         */
        hasDownloadButton: attr({
            default: false,
            compute() {
                if (!this.attachment || !this.attachmentList) {
                    return clear();
                }
                return !this.attachmentList.composerViewOwner && !this.attachment.isUploading;
            },
        }),
        /**
         * Determines the max height of this attachment image in px.
         */
        height: attr({
            required: true,
            compute() {
                if (!this.attachmentList) {
                    return clear();
                }
                if (this.attachmentList.composerViewOwner) {
                    return 50;
                }
                if (this.attachmentList.chatterOwner) {
                    return 160;
                }
                if (this.attachmentList.messageViewOwner) {
                    return 300;
                }
            },
        }),
        imageUrl: attr({
            compute() {
                if (!this.attachment) {
                    return;
                }
                if (
                    !this.attachment.accessToken &&
                    this.attachment.originThread &&
                    this.attachment.originThread.model === "mail.channel"
                ) {
                    return `/mail/channel/${this.attachment.originThread.id}/image/${this.attachment.id}/${this.width}x${this.height}`;
                }
                const accessToken = this.attachment.accessToken
                    ? `?access_token=${this.attachment.accessToken}`
                    : "";
                return `/web/image/${this.attachment.id}/${this.width}x${this.height}${accessToken}`;
            },
        }),
        /**
         * Determines the max width of this attachment image in px.
         */
        width: attr({
            required: true,
            /**
             * Returns an arbitrary high value, this is effectively a max-width and
             * the height should be more constrained.
             */
            compute() {
                return 1920;
            },
        }),
    },
});
