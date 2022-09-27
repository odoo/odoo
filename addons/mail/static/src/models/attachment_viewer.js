/** @odoo-module **/

import { registerModel } from '@mail/model/model_core';
import { attr, many, one } from '@mail/model/model_field';
import { clear, increment } from '@mail/model/model_field_command';

import { hidePDFJSButtons } from '@web/legacy/js/libs/pdfjs';

registerModel({
    name: 'AttachmentViewer',
    identifyingMode: 'xor',
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
         * Determine whether the current image is rendered for the 1st time, and if
         * that's the case, display a spinner until loaded.
         */
        handleImageLoad() {
            if (!this.exists() || !this.attachmentViewerViewable) {
                return;
            }
            if (
                this.attachmentViewerViewable.isImage &&
                (!this.imageRef || !this.imageRef.complete)
            ) {
                this.update({ isImageLoading: true });
            }
        },
        /**
         * @see 'hidePDFJSButtons'
         */
        hideUnwantedPdfJsButtons() {
            if (this.iframeViewerPdfRef.el) {
                hidePDFJSButtons(this.iframeViewerPdfRef.el);
            }
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
         * Called when clicking on zoom in icon.
         * @param {MouseEvent} ev
         */
        onClickZoomIn(ev) {
            ev.stopPropagation();
            this.zoomIn();
        },
        /**
         * Called when clicking on zoom out icon.
         * @param {MouseEvent} ev
         */
        onClickZoomOut(ev) {
            ev.stopPropagation();
            this.zoomOut();
        },
        /**
         * Called when clicking on reset zoom icon.
         *
         * @param {MouseEvent} ev
         */
        onClickZoomReset(ev) {
            ev.stopPropagation();
            this.resetZoom();
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
         * @param {DragEvent} ev
         */
        onMousedownImage(ev) {
            if (!this.exists()) {
                return;
            }
            if (this.isDragging) {
                return;
            }
            if (ev.button !== 0) {
                return;
            }
            ev.stopPropagation();
            this.update({
                isDragging: true,
                dragStartX: ev.clientX,
                dragStartY: ev.clientY,
            });
        },
        /**
         * @param {DragEvent}
         */
        onMousemoveView(ev) {
            if (!this.exists()) {
                return;
            }
            if (!this.isDragging) {
                return;
            }
            this.translate.update({
                dx: ev.clientX - this.dragStartX,
                dy: ev.clientY - this.dragStartY,
            });
            this.updateZoomerStyle();
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
         * Reset the zoom scale of the image.
         */
        resetZoom() {
            this.update({ scale: 1 });
            this.updateZoomerStyle();
        },
        /**
         * Rotate the image by 90 degrees to the right.
         */
        rotate() {
            this.update({ angle: this.angle + 90 });
        },
        /**
         * Stop dragging interaction of the user.
         */
        stopDragging() {
            this.update({ isDragging: false });
            this.translate.update({
                dx: 0,
                dy: 0,
                x: increment(this.translate.dx),
                y: increment(this.translate.dy),
            });
            this.updateZoomerStyle();
        },
        /**
         * Update the style of the zoomer based on translate transformation. Changes
         * are directly applied on zoomer, instead of triggering re-render and
         * defining them in the template, for performance reasons.
         */
        updateZoomerStyle() {
            const tx = this.imageRef.offsetWidth * this.scale > this.zoomerRef.el.offsetWidth
                ? this.translate.x + this.translate.dx
                : 0;
            const ty = this.imageRef.offsetHeight * this.scale > this.zoomerRef.el.offsetHeight
                ? this.translate.y + this.translate.dy
                : 0;
            if (tx === 0) {
                this.translate.update({ x: 0 });
            }
            if (ty === 0) {
                this.translate.update({ y: 0 });
            }
            this.zoomerRef.el.style = `transform: ` +
                `translate(${tx}px, ${ty}px)`;
        },
        /**
         * Zoom in the image.
         * @param {Object} [param0={}]
         * @param {boolean} [param0.scroll=false]
         */
        zoomIn({ scroll = false } = {}) {
            this.update({
                scale: this.scale + (scroll ? this.scrollZoomStep : this.zoomStep),
            });
            this.updateZoomerStyle();
        },
        /**
         * Zoom out the image.
         * @param {Object} [param0={}]
         * @param {boolean} [param0.scroll=false]
         */
        zoomOut({ scroll = false } = {}) {
            if (this.scale === this.minScale) {
                return;
            }
            const unflooredAdaptedScale = this.scale - (scroll ? this.scrollZoomStep : this.zoomStep);
            this.update({
                scale: Math.max(this.minScale, unflooredAdaptedScale),
            });
            this.updateZoomerStyle();
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
            compute() {
                if (this.attachmentList) {
                    return {
                        attachmentOwner: this.attachmentList.selectedAttachment,
                    };
                }
                return clear();
            },
        }),
        attachmentViewerViewables: many("AttachmentViewerViewable", {
            compute() {
                if (this.attachmentList) {
                    return this.attachmentList.viewableAttachments.map(attachment => {
                        return { attachmentOwner: attachment };
                    });
                }
                return clear();
            },
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
        dragStartX: attr({
            default: 0,
        }),
        dragStartY: attr({
            default: 0,
        }),
        /**
         * Reference of the IFRAME node when the attachment is a PDF.
         */
        iframeViewerPdfRef: attr(),
        imageRef: attr(),
        /**
         * Style of the image (scale + rotation).
         */
        imageStyle: attr({
            compute() {
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
        minScale: attr({
            default: 0.5,
        }),
        /**
         * Scale size of the image. Changes when user zooms in/out.
         */
        scale: attr({
            default: 1,
        }),
        scrollZoomStep: attr({
            default: 0.1,
        }),
        translate: one('AttachmentViewer.Translate', {
            default: {},
            inverse: 'owner',
        }),
        /**
         * Reference of the zoomer node. Useful to apply translate
         * transformation on image visualisation.
         */
        zoomerRef: attr(),
        zoomStep: attr({
            default: 0.5,
        }),
    },
});
