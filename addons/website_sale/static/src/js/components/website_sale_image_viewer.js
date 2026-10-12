import { onMounted, proxy, signal, t, useEffect, useListener, useProps } from "@odoo/owl";
import { Dialog } from "@web/core/dialog/dialog";
import { useHotkey } from "@web/core/hotkeys/hotkey_hook";
import { useDebounced } from "@web/core/utils/timing";

const ZOOM_STEP = 0.1;
const TOUCHMOVE_STEP = 96;

export class ProductImageViewer extends Dialog {
    static template = "website_sale.ProductImageViewer";

    viewerProps = useProps({
        images: t.array(t.instanceOf(HTMLImageElement)),
        selectedImageIdx: t.number().optional(0),
        imageRatio: t.string().optional("auto"),
        imageRatioMobile: t.string().optional("auto"),
    });

    imageContainerRef = signal.ref();
    /**
     * This is intentionally NOT reactive: this is to not render the whole component
     * just to update the style of {@link imageContainerRef}. It should be only
     * updated by {@link updateImageTranslate}.
     */
    imageTranslate = { x: 0, y: 0 };

    setup() {
        super.setup();

        this.images = this.viewerProps.images.map((image) => ({
            src: image.dataset.zoomImage || image.src,
            thumbnailSrc: image.src.replace("/image_1024/", "/image_256/"),
        }));
        this.state = proxy({
            selectedImageIdx: this.viewerProps.selectedImageIdx,
            imageScale: 1,
            carouselOffset: 0,
        });
        this.isDragging = false;
        this.dragStartPos = { x: 0, y: 0 };
        useHotkey("arrowleft", this.previousImage.bind(this));
        useHotkey("arrowright", this.nextImage.bind(this));
        useHotkey("r", () => {
            this.isDragging = false;
            this.state.imageScale = 1;
            this.updateImageTranslate({ x: 0, y: 0 });
        });

        // Debounce update in line with `ease-out` animation.
        this.updateCarousel = useDebounced(this._updateCarousel.bind(this), 250, {
            immediate: true,
            trailing: true,
        });

        // Not using a t-on-click on purpose because we want to be able to cancel the drag
        // when we go outside of the window.
        useListener(document, "click", this.onGlobalClick.bind(this));
        onMounted(() => {
            document
                .querySelector(".o_wsale_image_viewer_carousel li:last-of-type img")
                ?.addEventListener("load", this.updateCarousel.bind(this), { once: true });
        });

        /**
         * Reacts to reference changes
         * @see {@link imageTranslate}
         */
        useEffect(() => {
            this.updateImageTranslate();
        });
    }

    get selectedImage() {
        return this.images[this.state.selectedImageIdx];
    }

    set selectedImage(image) {
        this.state.imageScale = 1;
        this.state.selectedImageIdx = this.images.indexOf(image);
        this.updateCarousel();
        this.updateImageTranslate({ x: 0, y: 0 });
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
        this.selectedImage =
            this.images[
                (this.state.selectedImageIdx - 1 + this.images.length) % this.images.length
            ];
    }

    nextImage() {
        this.selectedImage = this.images[(this.state.selectedImageIdx + 1) % this.images.length];
    }

    /**
     * Method meant to be called to update {@link imageTranslate} to avoid a complete
     * render to assign its style attribute.
     *
     * @param {typeof this.imageTranslate} [nextImageTranslate]
     */
    updateImageTranslate(nextImageTranslate) {
        if (nextImageTranslate) {
            this.imageTranslate = nextImageTranslate;
        }
        this.imageContainerRef()?.setAttribute("style", this.imageContainerStyle);
    }

    /**
     * Centers the thumbnail row element on the currently selected image.
     *
     * @private
     */
    _updateCarousel() {
        const thumbnailList = document.querySelector(".o_wsale_image_viewer_carousel ol");
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
            if (
                this.dragStartPos.clientX === ev.clientX &&
                this.dragStartPos.clientY === ev.clientY
            ) {
                if (this.state.imageScale <= 1) {
                    this.zoomIn(ZOOM_STEP * 3);
                } else {
                    this.zoomOut(this.state.imageScale - 1);
                }
            }
        }
        if (ev.target.classList.contains("o_wsale_image_viewer_void") && !this.isDragging) {
            ev.stopPropagation();
            ev.preventDefault();
            this.data.close();
        } else {
            this.isDragging = false;
        }
    }

    zoomIn(step = undefined) {
        this.state.imageScale += step || ZOOM_STEP;
    }

    zoomOut(step = undefined) {
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
        this.updateImageTranslate({
            x: ev.clientX - this.dragStartPos.x,
            y: ev.clientY - this.dragStartPos.y,
        });
    }

    _onTouchstartCarousel(ev) {
        const touch = ev.touches?.item(0);
        if (!touch) {
            return;
        }
        this.state.touchClientX = touch.clientX;
        if (!this.state.touchmoveStep) {
            const thumbnail = document.querySelector("img.o_wsale_image_viewer_thumbnail");
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
