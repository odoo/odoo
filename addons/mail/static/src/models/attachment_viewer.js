/** @odoo-module **/

import { registerModel } from '@mail/model/model_core';
import { attr, many, one } from '@mail/model/model_field';

registerModel({
    name: 'AttachmentViewer',
    identifyingFields: ['dialogOwner'],
    recordMethods: {
        /**
         * Close the dialog with this attachment viewer.
         */
        close() {
            this.delete();
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
         * Display the next attachment in the list of attachments.
         */
        next() {
            if (!this.dialogOwner || !this.dialogOwner.attachmentListOwnerAsAttachmentView) {
                return;
            }
            this.dialogOwner.attachmentListOwnerAsAttachmentView.selectNextAttachment();
        },
        /**
         * Called when clicking on mask of attachment viewer.
         *
         * @param {MouseEvent} ev
         */
        onClick(ev) {
            if (this.isDragging) {
                return;
            }
            // TODO: clicking on the background should probably be handled by the dialog?
            // task-2092965
            this.close();
        },
        /**
         * Called when clicking on cross icon.
         *
         * @param {MouseEvent} ev
         */
        onClickClose(ev) {
            this.close();
        },
        /**
         * Called when clicking on download icon.
         *
         * @param {MouseEvent} ev
         */
        onClickDownload(ev) {
            ev.stopPropagation();
            this.attachment.download();
        },
        /**
         * Called when clicking on the header. Stop propagation of event to prevent
         * closing the dialog.
         *
         * @param {MouseEvent} ev
         */
        onClickHeader(ev) {
            ev.stopPropagation();
        },
        /**
         * Called when clicking on image. Stop propagation of event to prevent
         * closing the dialog.
         *
         * @param {MouseEvent} ev 
         */
        onClickImage(ev) {
            if (this.isDragging) {
                return;
            }
            ev.stopPropagation();
        },
        /**
         * Called when clicking on next icon.
         *
         * @param {MouseEvent} ev
         */
        onClickNext(ev) {
            ev.stopPropagation();
            this.next();
        },
        /**
         * Called when clicking on previous icon.
         *
         * @param {MouseEvent} ev
         */
        onClickPrevious(ev) {
            ev.stopPropagation();
            this.previous();
        },
        /**
         * Called when clicking on print icon.
         *
         * @param {MouseEvent} ev
         */
        onClickPrint(ev) {
            ev.stopPropagation();
            this.print();
        },
        /**
         * Called when clicking on rotate icon.
         *
         * @param {MouseEvent} ev
         */
        onClickRotate(ev) {
            ev.stopPropagation();
            this.rotate();
        },
        /**
         * Called when clicking on embed video player. Stop propagation to prevent
         * closing the dialog.
         *
         * @param {MouseEvent} ev
         */
        onClickVideo(ev) {
            ev.stopPropagation();
        },
        /**
         * Called when new image has been loaded
         *
         * @param {Event} ev
         */
        onLoadImage(ev) {
            if (!this.exists()) {
                return;
            }
            ev.stopPropagation();
            this.update({ isImageLoading: false });
        },
        /**
         * Display the previous attachment in the list of attachments.
         */
        previous() {
            if (!this.dialogOwner || !this.dialogOwner.attachmentListOwnerAsAttachmentView) {
                return;
            }
            this.dialogOwner.attachmentListOwnerAsAttachmentView.selectPreviousAttachment();
        },
        /**
         * Prompt the browser print of this attachment.
         */
        print() {
            const printWindow = window.open('about:blank', '_new');
            printWindow.document.open();
            printWindow.document.write(`
                <html>
                    <head>
                        <script>
                            function onloadImage() {
                                setTimeout('printImage()', 10);
                            }
                            function printImage() {
                                window.print();
                                window.close();
                            }
                        </script>
                    </head>
                    <body onload='onloadImage()'>
                        <img src="${this.imageUrl}" alt=""/>
                    </body>
                </html>`);
            printWindow.document.close();
        },
        /**
         * Rotate the image by 90 degrees to the right.
         */
        rotate() {
            this.update({ angle: this.angle + 90 });
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
