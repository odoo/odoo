import { onMounted, onRendered, useEffect, useRef, useState } from "@odoo/owl";
import { Dialog } from "@web/core/dialog/dialog";
import { useHotkey } from "@web/core/hotkeys/hotkey_hook";

const ZOOM_STEP = 0.1;
const TOUCHMOVE_STEP = 96;

export class ProductImageViewer extends Dialog {
    static template = "website_sale.ProductImageViewer";
    static props = {
        ...Dialog.props,
        images: { type: NodeList, required: true },
        selectedImageIdx: { type: Number, optional: true },
        imageRatio: { type: String, optional: true },
        close: Function,
    };

    setup() {
        super.setup();
        this.imageContainerRef = useRef("imageContainer");
        this.images = [...this.props.images].map(image => {
            return {
                src: image.dataset.zoomImage || image.src,
                thumbnailSrc: image.src.replace('/image_1024/', '/image_256/'),
            };
        });
        this.state = useState({
            selectedImageIdx: this.props.selectedImageIdx || 0,
            imageScale: 1,
            carouselOffset: 0,
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
        onMounted(() => {
            const carousel = document.querySelector('.o_wsale_image_viewer_carousel');
            if (carousel) {
                carousel.addEventListener('touchstart', this._onTouchstartCarousel.bind(this));
                carousel.addEventListener('touchmove', this._onTouchmoveCarousel.bind(this));
                const lastImg = carousel.querySelector('li:last-of-type img');
                lastImg?.addEventListener('load', this._updateCarousel.bind(this), { once: true });
            }
        });
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
        this._updateCarousel();
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

    /**
     * Centers the thumbnail row element on the currently selected image.
     *
     * @private
     */
    _updateCarousel() {
        const thumbnailList = document.querySelector('.o_wsale_image_viewer_carousel ol');
        const viewWidth = window.visualViewport.width;
        if (!thumbnailList || thumbnailList.scrollWidth <= viewWidth) {
            return;
        }
        const { selectedImageIdx } = this.state;
        const thumbnail = thumbnailList.childNodes[selectedImageIdx];
        const { left: thumbOffset, width: thumbWidth } = thumbnail.getBoundingClientRect();

        this.state.carouselOffset += (viewWidth - thumbWidth) / 2 - thumbOffset;
        thumbnailList.style.transform = `translate(${this.state.carouselOffset}px)`;
    }

    onGlobalClick(ev) {
        if (ev.target.tagName === "IMG") {
            // Only zoom if the image did not move
            if (this.dragStartPos.clientX === ev.clientX && this.dragStartPos.clientY === ev.clientY) {
                if (this.state.imageScale <= 1) {
                    this.zoomIn(ZOOM_STEP * 3);
                } else {
                    this.zoomOut(this.state.imageScale - 1);
                }
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
        if (!ev.deltaY) {
            return;
        }
        ev.preventDefault();
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

    _onTouchstartCarousel(ev) {
        const touch = ev.touches?.item(0);
        if (!touch) {
            return;
        }
        this.state.touchClientX = touch.clientX;
        if (!this.state.touchmoveStep) {
            const thumbnail = document.querySelector('img.o_wsale_image_viewer_thumbnail');
            this.state.touchmoveStep = 0.75 * thumbnail?.clientWidth;
        }
    }

    _onTouchmoveCarousel(ev) {
        const touch = ev.touches?.item(0);
        if (!touch) {
            return;
        }
        ev.preventDefault();
        const { selectedImageIdx, touchmoveStep, touchClientX } = this.state;
        const deltaX = touch.clientX - touchClientX;
        const step = touchmoveStep || TOUCHMOVE_STEP;
        if (deltaX > step && selectedImageIdx > 0) {
            this.state.touchClientX += step;
            this.previousImage();
        } else if (deltaX < -step && selectedImageIdx < this.images.length - 1) {
            this.state.touchClientX -= step;
            this.nextImage();
        }
    }
}
delete ProductImageViewer.props.slots;
