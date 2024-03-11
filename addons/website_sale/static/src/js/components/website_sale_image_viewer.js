/** @odoo-module **/

import { useWowlService } from '@web/legacy/utils';
import { Dialog } from "@web/core/dialog/dialog";
import { useHotkey } from "@web/core/hotkeys/hotkey_hook";

const { Component, onRendered, useRef, useEffect, useState, xml } = owl;

const ZOOM_STEP = 0.1;

export class ProductImageViewer extends Dialog {
    setup() {
        super.setup();
        this.imageContainerRef = useRef("imageContainer");
        this.images = [...this.props.images].map(image => {
            return {
                src: image.dataset.zoomImage || image.src,
                thumbnailSrc: image.src.replace('/image_1024/', '/image_128/'),
            };
        });
        this.state = useState({
            selectedImageIdx: this.props.selectedImageIdx || 0,
            imageScale: 1,
        });
        this.isDragging = false;
        this.dragStartPos = { x: 0, y: 0 };
        // Doing a full render for the translate is too slow.
        this.imageTranslate = { x: 0, y: 0 };
        useHotkey("arrowleft", this.previousImage.bind(this));
        useHotkey("arrowright", this.nextImage.bind(this));
        useHotkey("r", () => {
            this.imageTranslate = { x: 0, y: 0 };
            this.isDragging = false;
            this.state.imageScale = 1;
            this.updateImage();
        });

        // Not using a t-on-click on purpose because we want to be able to cancel the drag
        // when we go outside of the window.
        useEffect(
            (document) => {
                const onGlobalClick = this.onGlobalClick.bind(this);
                document.addEventListener("click", onGlobalClick);
                return () => {document.removeEventListener("click", onGlobalClick)};
            },
            () => [document],
        );
        // For some reason the styling does not always update properly.
        onRendered(() => {
            this.updateImage();
        })
    }

    get selectedImage() {
        return this.images[this.state.selectedImageIdx];
    }

    set selectedImage(image) {
        this.state.imageScale = 1;
        this.imageTranslate = { x: 0, y: 0 };
        this.state.selectedImageIdx = this.images.indexOf(image);
    }

    get imageStyle() {
        return `transform:
            scale3d(${this.state.imageScale}, ${this.state.imageScale}, 1);
        `;
    }

    get imageContainerStyle() {
        return `transform: translate(${this.imageTranslate.x}px, ${this.imageTranslate.y}px);`;
    }

    previousImage() {
        this.selectedImage = this.images[(this.state.selectedImageIdx - 1 + this.images.length) % this.images.length];
    }

    nextImage() {
        this.selectedImage = this.images[(this.state.selectedImageIdx + 1) % this.images.length];
    }

    updateImage() {
        if (!this.imageContainerRef || !this.imageContainerRef.el) {
            return;
        }
        this.imageContainerRef.el.style = this.imageContainerStyle;
    }

    onGlobalClick(ev) {
        if (ev.target.tagName === "IMG") {
            // Only zoom if the image did not move
            if (this.dragStartPos.clientX === ev.clientX && this.dragStartPos.clientY === ev.clientY) {
                this.zoomIn(ZOOM_STEP * 3);
            }
        }
        if (ev.target.classList.contains('o_wsale_image_viewer_void') && !this.isDragging) {
            ev.stopPropagation();
            ev.preventDefault();
            this.data.close();
        } else {
            this.isDragging = false;
        }
    }

    zoomIn(step=undefined) {
        this.state.imageScale += step || ZOOM_STEP;
    }

    zoomOut(step=undefined) {
        this.state.imageScale = Math.max(0.5, this.state.imageScale - (step || ZOOM_STEP));
    }

    onWheelImage(ev) {
        if (ev.deltaY > 0) {
            this.zoomOut();
        } else {
            this.zoomIn();
        }
    }

    onMousedownImage(ev) {
        this.isDragging = true;
        this.dragStartPos = {
            x: ev.clientX - this.imageTranslate.x,
            y: ev.clientY - this.imageTranslate.y,
            clientX: ev.clientX,
            clientY: ev.clientY,
        };
    }

    onGlobalMousemove(ev) {
        if (!this.isDragging) {
            return;
        }
        this.imageTranslate.x = ev.clientX - this.dragStartPos.x;
        this.imageTranslate.y = ev.clientY - this.dragStartPos.y;
        this.updateImage();
    }
}
ProductImageViewer.props = {
    ...Dialog.props,
    images: { type: NodeList, required: true },
    selectedImageIdx: { type: Number, optional: true },
    close: Function,
};
delete ProductImageViewer.props.slots;
ProductImageViewer.template = "website_sale.ProductImageViewer";

export class ProductImageViewerWrapper extends Component {
    setup() {
        this.dialogs = useWowlService('dialog');

        onRendered(() => {
            this.dialogs.add(ProductImageViewer, this.props);
        });
    }
}
ProductImageViewerWrapper.template = xml``;
