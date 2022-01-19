/** @odoo-module **/

import { registerModel } from '@mail/model/model_core';
import { attr, many, one } from '@mail/model/model_field';

registerModel({
    name: 'AttachmentViewer',
    identifyingFields: ['attachmentList'],
    recordMethods: {
        /**
         * Close the attachment viewer by closing its linked dialog.
         */
        close() {
            const dialog = this.messaging.models['Dialog'].find(dialog => dialog.record === this);
            if (dialog) {
                dialog.delete();
            }
        },
        /**
         * Returns whether the given html element is inside this attachment viewer.
         *
         * @param {Element} element
         * @returns {boolean}
         */
        containsElement(element) {
            return Boolean(this.component && this.component.root.el && this.component.root.el.contains(element));
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
                return `/mail/channel/${this.attachment.originThread.id}/image/${this.attachment.id}`;
            }
            const accessToken = this.attachment.accessToken ? `?access_token=${this.attachment.accessToken}` : '';
            return `/web/image/${this.attachment.id}${accessToken}`;
        },
    },
    fields: {
        /**
         * Angle of the image. Changes when the user rotates it.
         */
        angle: attr({
            default: 0,
        }),
        attachment: one('Attachment'),
        attachmentList: one('AttachmentList', {
            readonly: true,
            required: true,
        }),
        attachments: many('Attachment', {
            related: 'attachmentList.viewableAttachments',
        }),
        /**
         * States the OWL component of this attachment viewer.
         */
        component: attr(),
        /**
         * Determines the dialog displaying this attachment viewer.
         */
        dialog: one('Dialog', {
            inverse: 'attachmentViewer',
            isCausal: true,
            readonly: true,
        }),
        /**
         * Determines the source URL to use for the image.
         */
        imageUrl: attr({
            compute: '_computeImageUrl',
            readonly: true,
        }),
        /**
         * Determine whether the user is currently dragging the image.
         * This is useful to determine whether a click outside of the image
         * should close the attachment viewer or not.
         */
        isDragging: attr({
            default: false,
        }),
        /**
         * Determine whether the image is loading or not. Useful to diplay
         * a spinner when loading image initially.
         */
        isImageLoading: attr({
            default: false,
        }),
        /**
         * Scale size of the image. Changes when user zooms in/out.
         */
        scale: attr({
            default: 1,
        }),
    },
});
