/** @odoo-module **/

import { registerModel } from '@mail/model/model_core';
import { attr, many, one } from '@mail/model/model_field';
import { clear } from '@mail/model/model_field_command';

registerModel({
    name: 'AttachmentViewer',
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
            this.attachmentViewerViewable.download();
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
         */
        _computeAttachmentViewerViewable() {
            if (this.attachmentList) {
                return {
                    attachmentOwner: this.attachmentList.selectedAttachment,
                };
            }
            return clear();
        },
        /**
         * @private
         */
        _computeAttachmentViewerViewables() {
            if (this.attachmentList) {
                return this.attachmentList.viewableAttachments.map(attachment => {
                    return { attachmentOwner: attachment };
                });
            }
            return clear();
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
        attachmentList: one('AttachmentList', {
            related: 'dialogOwner.attachmentListOwnerAsAttachmentView',
        }),
        attachmentViewerViewable: one("AttachmentViewerViewable", {
            compute: "_computeAttachmentViewerViewable",
        }),
        attachmentViewerViewables: many("AttachmentViewerViewable", {
            compute: "_computeAttachmentViewerViewables",
        }),
        /**
         * States the OWL component of this attachment viewer.
         */
        component: attr(),
        /**
         * Determines the dialog displaying this attachment viewer.
         */
        dialogOwner: one('Dialog', {
            identifying: true,
            inverse: 'attachmentViewer',
            isCausal: true,
        }),
        /**
         * Style of the image (scale + rotation).
         */
        imageStyle: attr({
            compute: '_computeImageStyle',
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
