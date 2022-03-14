/** @odoo-module **/

import { registerModel } from '@mail/model/model_core';
import { attr, many, one } from '@mail/model/model_field';

registerModel({
    name: 'AttachmentViewer',
    identifyingFields: ['dialogOwner'],
    recordMethods: {
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
        /**
         * @private
         * @returns {string}
         */
        _computeImageStyle() {
            let style = `transform: ` +
                `scale3d(${this.scale}, ${this.scale}, 1) ` +
                `rotate(${this.angle}deg);`;

            if (this.angle % 180 !== 0) {
                style += `` +
                    `max-height: ${window.innerWidth}px; ` +
                    `max-width: ${window.innerHeight}px;`;
            } else {
                style += `` +
                    `max-height: 100%; ` +
                    `max-width: 100%;`;
            }
            return style;
        },
    },
    fields: {
        /**
         * Angle of the image. Changes when the user rotates it.
         */
        angle: attr({
            default: 0,
        }),
        attachment: one('Attachment', {
            related: 'attachmentList.selectedAttachment',
        }),
        attachmentList: one('AttachmentList', {
            related: 'dialogOwner.attachmentListOwnerAsAttachmentView',
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
        dialogOwner: one('Dialog', {
            inverse: 'attachmentViewer',
            isCausal: true,
            readonly: true,
        }),
        /**
         * Style of the image (scale + rotation).
         */
        imageStyle: attr({
            compute: '_computeImageStyle',
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
