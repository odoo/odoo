/** @odoo-module **/

import {applyModifications, cropperDataFields, activateCropper, loadImage, loadImageInfo} from "@web_editor/js/editor/image_processing";
import { _t } from "@web/core/l10n/translation";
import {
    Component,
    useRef,
    useState,
    onMounted,
    onWillDestroy,
    onWillUpdateProps,
    markup,
} from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";
import dom from "@web/legacy/js/core/dom";
import { preserveCursor } from "@web_editor/js/editor/odoo-editor/src/utils/utils";

export class ImageCrop extends Component {
    static template = 'web_editor.ImageCrop';
    static props = {
        rpc: Function,
        showCount: { type: Number, optional: true },
        activeOnStart: { type: Boolean, optional: true },
        media: { optional: true },
        mimetype: { type: String, optional: true },
        mimetypeOutputAttribute: { type: String, optional: true },
    };
    static defaultProps = {
        activeOnStart: false,
        showCount: 0,
        mimetypeOutputAttribute: "mimetype",
    };
    aspectRatios = {
        "0/0": {label: _t("Flexible"), value: 0},
        "16/9": {label: "16:9", value: 16 / 9},
        "4/3": {label: "4:3", value: 4 / 3},
        "1/1": {label: "1:1", value: 1},
        "2/3": {label: "2:3", value: 2 / 3},
    };
    state = useState({
        active: false,
    });

    elRef = useRef('el');
    _cropperClosed = true;

    setup() {
        // This promise is resolved when the component is mounted. It is
        // required by a legacy mechanism to wait for the component to be
        // mounted. See `ImageTools.resetCrop`.
        this.mountedPromise = new Promise((resolve) => {
            this.mountedResolve = resolve;
        });
        this.notification = useService("notification");
        onMounted(async () => {
            const $el = $(this.elRef.el);
            this.$ = $el.find.bind($el);
            this.$('[data-action]').on('click', this._onCropOptionClick.bind(this));
            $el.on('zoom', this._onCropZoom.bind(this));
            if (this.props.activeOnStart) {
                this.state.active = true;
                await this._show(this.props);
            }
            this.mountedResolve();
        });
        onWillUpdateProps((newProps) => {
            if (newProps.showCount !== this.props.showCount) {
                this.state.active = true;
            }
            return this._show(newProps);
        });
        onWillDestroy(() => {
            this._closeCropper();
        });
    }

    _closeCropper() {
        if (this._cropperClosed) return;
        this._cropperClosed = true;
        if (this.$cropperImage) {
            this.$cropperImage.cropper('destroy');
            this.elRef.el.ownerDocument.removeEventListener('mousedown', this._onDocumentMousedown, {capture: true});
            this.elRef.el.ownerDocument.removeEventListener('keydown', this._onDocumentKeydown, {capture: true});
        }
        this.media.setAttribute('src', this.initialSrc);
        this.media.dataset[this.props.mimetypeOutputAttribute] = this.mimetype;
        this.$media.trigger('image_cropper_destroyed');
        this.state.active = false;
        this.restoreCursor();
    }

    /**
     * Resets the crop
     */
    async reset() {
        if (this.$cropperImage) {
            this.$cropperImage.cropper('reset');
            if (this.aspectRatio !== '0/0') {
                this.aspectRatio = '0/0';
                this.$cropperImage.cropper('setAspectRatio', this.aspectRatios[this.aspectRatio].value);
            }
            await this._save(false);
        }
    }

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * @override
     */
    async _show(props) {
        if (!props.media || !this.state.active) {
            return;
        }
        this._cropperClosed = false;
        this.media = props.media;
        this.$media = $(this.media);
        // Needed for editors in iframes.
        this.document = this.media.ownerDocument;
        this.restoreCursor = preserveCursor(this.media.ownerDocument);
        // key: ratio identifier, label: displayed to user, value: used by cropper lib
        const src = this.media.getAttribute('src');
        const data = {...this.media.dataset};
        this.initialSrc = src;
        this.aspectRatio = data.aspectRatio || "0/0";
        const mimetype = data.mimetype ||
                src.endsWith('.png') ? 'image/png' :
                src.endsWith('.webp') ? 'image/webp' :
                'image/jpeg';
        this.mimetype = this.props.mimetype || mimetype;

        await loadImageInfo(this.media, this.props.rpc);
        const isIllustration = /^\/web_editor\/shape\/illustration\//.test(this.media.dataset.originalSrc);
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
                markup(_t("This type of image is not supported for cropping.<br/>If you want to crop it, please first download it from the original source and upload it in Odoo.")),
                {
                    title: _t("This image is an external image"),
                    type: 'warning',
                }
            )
            return this._closeCropper();
        }
        const $cropperWrapper = this.$('.o_we_cropper_wrapper');

        await this._scrollToInvisibleImage();
        // Replacing the src with the original's so that the layout is correct.
        await loadImage(this.originalSrc, this.media);
        this.$cropperImage = this.$('.o_we_cropper_img');
        const cropperImage = this.$cropperImage[0];
        [cropperImage.style.width, cropperImage.style.height] = [this.$media.width() + 'px', this.$media.height() + 'px'];
        
        const sel = this.document.getSelection();
        sel && sel.removeAllRanges();

        // Overlaying the cropper image over the real image
        const offset = this.$media.offset();
        offset.left += parseInt(this.$media.css('padding-left'));
        offset.top += parseInt(this.$media.css('padding-right'));
        $cropperWrapper[0].style.left = `${offset.left}px`;
        $cropperWrapper[0].style.top = `${offset.top}px`;

        await loadImage(this.originalSrc, cropperImage);

        // We need to remove the d-none class for the cropper library to work.
        this.elRef.el.classList.remove('d-none');
        await activateCropper(cropperImage, this.aspectRatios[this.aspectRatio].value, this.media.dataset);

        this._onDocumentMousedown = this._onDocumentMousedown.bind(this);
        this._onDocumentKeydown = this._onDocumentKeydown.bind(this);
        // We use capture so that the handler is called before other editor handlers
        // like save, such that we can restore the src before a save.
        // We need to add event listeners to the owner document of the widget.
        this.elRef.el.ownerDocument.addEventListener('mousedown', this._onDocumentMousedown, {capture: true});
        this.elRef.el.ownerDocument.addEventListener('keydown', this._onDocumentKeydown, {capture: true});
    }
    /**
     * Updates the DOM image with cropped data and associates required
     * information for a potential future save (where required cropped data
     * attachments will be created).
     *
     * @private
     * @param {boolean} [cropped=true]
     */
    async _save(cropped = true) {
        // Mark the media for later creation of cropped attachment
        this.media.classList.add('o_modified_image_to_save');

        [...cropperDataFields, 'aspectRatio'].forEach(attr => {
            delete this.media.dataset[attr];
            const value = this._getAttributeValue(attr);
            if (value) {
                this.media.dataset[attr] = value;
            }
        });
        delete this.media.dataset.resizeWidth;
        const { dataURL, mimetype } = await applyModifications(
            this.media,
            { forceModification: true, mimetype: this.mimetype },
            true // TODO: remove in master
        );
        this.initialSrc = dataURL;
        this.mimetype = mimetype;
        this.media.classList.toggle('o_we_image_cropped', cropped);
        this.$media.trigger('image_cropped');
        this._closeCropper();
    }
    /**
     * Returns an attribute's value for saving.
     *
     * @private
     */
    _getAttributeValue(attr) {
        if (cropperDataFields.includes(attr)) {
            return this.$cropperImage.cropper('getData')[attr];
        }
        return this[attr];
    }
    /**
     * Resets the crop box to prevent it going outside the image.
     *
     * @private
     */
    _resetCropBox() {
        this.$cropperImage.cropper('clear');
        this.$cropperImage.cropper('crop');
    }
    /**
     * Make sure the targeted image is in the visible viewport before crop.
     *
     * @private
     */
    async _scrollToInvisibleImage() {
        const rect = this.media.getBoundingClientRect();
        const viewportTop = this.document.documentElement.scrollTop || 0;
        const viewportBottom = viewportTop + window.innerHeight;
        const closestScrollable = el => {
            if (!el) {
                return null;
            }
            if (el.scrollHeight > el.clientHeight) {
                return $(el);
            } else {
                return closestScrollable(el.parentElement);
            }
        };
        // Give priority to the closest scrollable element (e.g. for images in
        // HTML fields, the element to scroll is different from the document's
        // scrolling element).
        const $scrollable = closestScrollable(this.media);

        // The image must be in a position that allows access to it and its crop
        // options buttons. Otherwise, the crop widget container can be scrolled
        // to allow editing.
        if (rect.top < viewportTop || viewportBottom - rect.bottom < 100) {
            await dom.scrollTo(this.media, {
                easing: "linear",
                duration: 500,
                ...($scrollable && { $scrollable }),
            });
        }
    }

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    /**
     * Called when a crop option is clicked -> change the crop area accordingly.
     *
     * @private
     * @param {MouseEvent} ev
     */
    _onCropOptionClick(ev) {
        const {action, value, scaleDirection} = ev.currentTarget.dataset;
        switch (action) {
            case 'ratio':
                this.$cropperImage.cropper('reset');
                this.aspectRatio = value;
                this.$cropperImage.cropper('setAspectRatio', this.aspectRatios[this.aspectRatio].value);
                break;
            case 'zoom':
            case 'reset':
                this.$cropperImage.cropper(action, value);
                break;
            case 'rotate':
                this.$cropperImage.cropper(action, value);
                this._resetCropBox();
                break;
            case 'flip': {
                const amount = this.$cropperImage.cropper('getData')[scaleDirection] * -1;
                return this.$cropperImage.cropper(scaleDirection, amount);
            }
            case 'apply':
                return this._save();
            case 'discard':
                return this._closeCropper();
        }
    }
    /**
     * Discards crop if the user clicks outside of the widget.
     *
     * @private
     * @param {MouseEvent} ev
     */
    _onDocumentMousedown(ev) {
        if (this.elRef.el.ownerDocument.body.contains(ev.target) && this.$(ev.target).length === 0) {
            return this._closeCropper();
        }
    }
    /**
     * Save crop if user hits enter,
     * discard crop on escape.
     *
     * @private
     * @param {KeyboardEvent} ev
     */
    _onDocumentKeydown(ev) {
        if (ev.key === 'Enter') {
            return this._save();
        } else if (ev.key === 'Escape') {
            ev.stopImmediatePropagation();
            return this._closeCropper();
        }
    }
    /**
     * Resets the cropbox on zoom to prevent crop box overflowing.
     *
     * @private
     */
    async _onCropZoom() {
        // Wait for the zoom event to be fully processed before reseting.
        await new Promise(res => setTimeout(res, 0));
        this._resetCropBox();
    }
}
