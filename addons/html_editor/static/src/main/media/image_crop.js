import {
    applyModifications,
    cropperDataFields,
    activateCropper,
    loadImage,
    loadImageInfo,
} from "@html_editor/utils/image_processing";
import { _t } from "@web/core/l10n/translation";
import {
    Component,
    useRef,
    onMounted,
    onWillDestroy,
    markup,
    useExternalListener,
    status,
} from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";
import { scrollTo, closestScrollableY } from "@web/core/utils/scrolling";

export class ImageCrop extends Component {
    static template = "html_editor.ImageCrop";
    static props = {
        document: { validate: (p) => p.nodeType === Node.DOCUMENT_NODE },
        media: { optional: true },
        mimetype: { type: String, optional: true },
        onClose: { type: Function, optional: true },
        onSave: { type: Function, optional: true },
    };

    setup() {
        this.aspectRatios = {
            "0/0": { label: _t("Flexible"), value: 0 },
            "16/9": { label: "16:9", value: 16 / 9 },
            "4/3": { label: "4:3", value: 4 / 3 },
            "1/1": { label: "1:1", value: 1 },
            "2/3": { label: "2:3", value: 2 / 3 },
        };
        this.notification = useService("notification");
        this.media = this.props.media;
        this.document = this.props.document;

        this.elRef = useRef("el");
        this.cropperWrapper = useRef("cropperWrapper");
        this.imageRef = useRef("imageRef");
        this.cropperOpen = false;

        // We use capture so that the handler is called before other editor handlers
        // like save, such that we can restore the src before a save.
        // We need to add event listeners to the owner document of the widget.
        useExternalListener(this.document, "mousedown", this.onDocumentMousedown, {
            capture: true,
        });
        useExternalListener(this.document, "keydown", this.onDocumentKeydown, {
            capture: true,
        });

        onMounted(() => {
            this.hasModifiedImageClass = this.media.classList.contains("o_modified_image_to_save");
            if (this.hasModifiedImageClass) {
                this.media.classList.remove("o_modified_image_to_save");
            }
            this.show();
        });
        onWillDestroy(this.closeCropper);
    }

    closeCropper() {
        if (!this.cropperOpen) {
            return;
        }
        this.cropper?.destroy?.();
        this.media.setAttribute("src", this.initialSrc);
        if (
            this.hasModifiedImageClass &&
            !this.media.classList.contains("o_modified_image_to_save")
        ) {
            this.media.classList.add("o_modified_image_to_save");
        }
        this.props?.onClose?.();
        this.cropperOpen = false;
    }

    /**
     * Resets the crop
     */
    async reset() {
        if (this.cropper) {
            this.cropper.reset();
            if (this.aspectRatio !== "0/0") {
                this.aspectRatio = "0/0";
                this.cropper.setAspectRatio(this.aspectRatios[this.aspectRatio].value);
            }
            await this.save(false);
        }
    }

    async show() {
        if (this.cropperOpen) {
            return;
        }
        // key: ratio identifier, label: displayed to user, value: used by cropper lib
        const src = this.media.getAttribute("src");
        const data = { ...this.media.dataset };
        this.initialSrc = src;
        this.aspectRatio = data.aspectRatio || "0/0";
        const mimetype =
            data.mimetype || src.endsWith(".png")
                ? "image/png"
                : src.endsWith(".webp")
                ? "image/webp"
                : "image/jpeg";
        this.mimetype = this.props.mimetype || mimetype;

        await loadImageInfo(this.media);
        const isIllustration = /^\/(?:html|web)_editor\/shape\/illustration\//.test(
            this.media.dataset.originalSrc
        );
        this.uncroppable = false;
        if (this.media.dataset.originalSrc && !isIllustration) {
            this.originalSrc = this.media.dataset.originalSrc;
            this.originalId = this.media.dataset.originalId;
        } else {
            // Couldn't find an attachment: not croppable.
            this.uncroppable = true;
        }

        if (this.uncroppable) {
            this.notification.add(
                markup(
                    _t(
                        "This type of image is not supported for cropping.<br/>If you want to crop it, please first download it from the original source and upload it in Odoo."
                    )
                ),
                {
                    title: _t("This image is an external image"),
                    type: "warning",
                }
            );
            return this.closeCropper();
        }

        await this.scrollToInvisibleImage();
        // Replacing the src with the original's so that the layout is correct.
        await loadImage(this.originalSrc, this.media);
        if (status(this) !== "mounted") {
            // Abort if the component has been destroyed in the meantime
            // since `this.imageRef.el` is `null` when it is not mounted.
            return;
        }
        const cropperImage = this.imageRef.el;
        [cropperImage.style.width, cropperImage.style.height] = [
            this.media.width + "px",
            this.media.height + "px",
        ];

        const sel = this.document.getSelection();
        sel && sel.removeAllRanges();

        // Overlaying the cropper image over the real image
        let offset = undefined;
        if (!this.media.getClientRects().length) {
            offset = { top: 0, left: 0 };
        } else {
            const rect = this.media.getBoundingClientRect();
            const win = this.media.ownerDocument.defaultView;
            offset = {
                top: rect.top + win.pageYOffset,
                left: rect.left + win.pageXOffset,
            };
        }

        offset.left += parseInt(this.media.style.paddingLeft || 0);
        offset.top += parseInt(this.media.style.paddingRight || 0);
        const frameElement = this.media.ownerDocument.defaultView.frameElement;
        if (frameElement) {
            const frameRect = frameElement.getBoundingClientRect();
            offset.left += frameRect.left;
            offset.top += frameRect.top;
        }

        this.cropperWrapper.el.style.left = `${offset.left}px`;
        this.cropperWrapper.el.style.top = `${offset.top}px`;

        await loadImage(this.originalSrc, cropperImage);

        this.cropper = await activateCropper(
            cropperImage,
            this.aspectRatios[this.aspectRatio].value,
            this.media.dataset
        );
        this.cropperOpen = true;
    }
    /**
     * Updates the DOM image with cropped data and associates required
     * information for a potential future save (where required cropped data
     * attachments will be created).
     *
     * @private
     * @param {boolean} [cropped=true]
     */
    async save(cropped = true) {
        // Mark the media for later creation of cropped attachment
        this.media.classList.add("o_modified_image_to_save");

        [...cropperDataFields, "aspectRatio"].forEach((attr) => {
            delete this.media.dataset[attr];
            const value = this.getAttributeValue(attr);
            if (value) {
                this.media.dataset[attr] = value;
            }
        });
        delete this.media.dataset.resizeWidth;
        this.initialSrc = await applyModifications(this.media, this.cropper, {
            forceModification: true,
            mimetype: this.mimetype,
        });
        this.media.classList.toggle("o_we_image_cropped", cropped);
        this.closeCropper();
        this.props.onSave?.();
    }
    /**
     * Returns an attribute's value for saving.
     *
     * @private
     */
    getAttributeValue(attr) {
        if (cropperDataFields.includes(attr)) {
            return this.cropper.getData()[attr];
        }
        return this[attr];
    }
    /**
     * Resets the crop box to prevent it going outside the image.
     *
     * @private
     */
    resetCropBox() {
        this.cropper.clear();
        this.cropper.crop();
    }
    /**
     * Make sure the targeted image is in the visible viewport before crop.
     *
     * @private
     */
    async scrollToInvisibleImage() {
        const rect = this.media.getBoundingClientRect();
        const viewportTop = this.document.documentElement.scrollTop || 0;
        const viewportBottom = viewportTop + window.innerHeight;
        // Give priority to the closest scrollable element (e.g. for images in
        // HTML fields, the element to scroll is different from the document's
        // scrolling element).
        const scrollable = closestScrollableY(this.media);

        // The image must be in a position that allows access to it and its crop
        // options buttons. Otherwise, the crop widget container can be scrolled
        // to allow editing.
        if (rect.top < viewportTop || viewportBottom - rect.bottom < 100) {
            await scrollTo(this.media, {
                behavior: "smooth",
                ...(scrollable && { scrollable }),
            });
        }
    }

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    onZoom(scale) {
        this.cropper.zoom(scale);
    }

    onReset() {
        this.cropper.reset();
    }

    onRotate(degree) {
        this.cropper.rotate(degree);
        this.resetCropBox();
    }

    onFlip(scaleDirection) {
        const amount = this.cropper.getData()[scaleDirection] * -1;
        this.cropper[scaleDirection](amount);
    }

    setAspectRatio(ratio) {
        this.cropper.reset();
        this.aspectRatio = ratio;
        this.cropper.setAspectRatio(this.aspectRatios[this.aspectRatio].value);
    }

    /**
     * Discards crop if the user clicks outside of the widget.
     *
     * @private
     * @param {MouseEvent} ev
     */
    onDocumentMousedown(ev) {
        if (
            this.props.document.body.contains(ev.target) &&
            (this.elRef.el === ev.target || !this.elRef.el.contains(ev.target))
        ) {
            return this.closeCropper();
        }
    }
    /**
     * Save crop if user hits enter,
     * discard crop on escape.
     *
     * @private
     * @param {KeyboardEvent} ev
     */
    onDocumentKeydown(ev) {
        if (ev.key === "Enter") {
            return this.save();
        } else if (ev.key === "Escape") {
            ev.stopImmediatePropagation();
            return this.closeCropper();
        }
    }
    /**
     * Resets the cropbox on zoom to prevent crop box overflowing.
     *
     * @private
     */
    async onCropZoom() {
        // Wait for the zoom event to be fully processed before reseting.
        await new Promise((res) => setTimeout(res, 0));
        this.resetCropBox();
    }
}
