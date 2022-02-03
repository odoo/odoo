/** @odoo-module **/

import { registerModel } from '@mail/model/model_core';
import { attr, one } from '@mail/model/model_field';
import { clear, insertAndReplace, replace } from '@mail/model/model_field_command';

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
            readonly: true,
            required: true,
        }),
        attachmentDeleteConfirmDialog: one('Dialog', {
            inverse: 'attachmentImageOwnerAsAttachmentDeleteConfirm',
            isCausal: true,
        }),
        /**
         * States the attachmentList displaying this attachment image.
         */
        attachmentList: one('AttachmentList', {
            inverse: 'attachmentImages',
            readonly: true,
            required: true,
        }),
        /**
         * States the OWL component of this attachment image.
         */
        component: attr(),
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
