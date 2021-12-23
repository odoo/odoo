odoo.define('wysiwyg.widgets.ImageCropWidget', function (require) {
'use strict';

const core = require('web.core');
const Widget = require('web.Widget');
const {applyModifications, cropperDataFields, activateCropper, loadImage, loadImageInfo} = require('web_editor.image_processing');

const _t = core._t;

const ImageCropWidget = Widget.extend({
    template: ['wysiwyg.widgets.crop'],
    xmlDependencies: ['/web_editor/static/src/xml/wysiwyg.xml'],
    events: {
        'click.crop_options [data-action]': '_onCropOptionClick',
        // zoom event is triggered by the cropperjs library when the user zooms.
        'zoom': '_onCropZoom',
    },

    /**
     * @constructor
     */
    init(parent, media) {
        this._super(...arguments);
        this.media = media;
        this.$media = $(media);
        // Needed for editors in iframes.
        this.document = media.ownerDocument;
        // key: ratio identifier, label: displayed to user, value: used by cropper lib
        this.aspectRatios = {
            "0/0": {label: _t("Free"), value: 0},
            "16/9": {label: "16:9", value: 16 / 9},
            "4/3": {label: "4:3", value: 4 / 3},
            "1/1": {label: "1:1", value: 1},
            "2/3": {label: "2:3", value: 2 / 3},
        };
        const src = this.media.getAttribute('src');
        const data = Object.assign({}, media.dataset);
        this.initialSrc = src;
        this.aspectRatio = data.aspectRatio || "0/0";
        this.mimetype = data.mimetype || src.endsWith('.png') ? 'image/png' : 'image/jpeg';
    },
    /**
     * @override
     */
    async willStart() {
        await this._super.apply(this, arguments);
        await loadImageInfo(this.media, this._rpc.bind(this));
        const isIllustration = /^\/web_editor\/shape\/illustration\//.test(this.media.dataset.originalSrc);
        if (this.media.dataset.originalSrc && !isIllustration) {
            this.originalSrc = this.media.dataset.originalSrc;
            this.originalId = this.media.dataset.originalId;
            return;
        }
        // Couldn't find an attachment: not croppable.
        this.uncroppable = true;
    },
    /**
     * @override
     */
    async start() {
        if (this.uncroppable) {
            this.displayNotification({
              type: 'warning',
              title: _t("This image is an external image"),
              message: _t("This type of image is not supported for cropping.<br/>If you want to crop it, please first download it from the original source and upload it in Odoo."),
            });
            return this.destroy();
        }
        const _super = this._super.bind(this);
        const $cropperWrapper = this.$('.o_we_cropper_wrapper');

        // Replacing the src with the original's so that the layout is correct.
        await loadImage(this.originalSrc, this.media);
        this.$cropperImage = this.$('.o_we_cropper_img');
        const cropperImage = this.$cropperImage[0];
        [cropperImage.style.width, cropperImage.style.height] = [this.$media.width() + 'px', this.$media.height() + 'px'];

        // Overlaying the cropper image over the real image
        const offset = this.$media.offset();
        offset.left += parseInt(this.$media.css('padding-left'));
        offset.top += parseInt(this.$media.css('padding-right'));
        $cropperWrapper.offset(offset);

        await loadImage(this.originalSrc, cropperImage);
        await activateCropper(cropperImage, this.aspectRatios[this.aspectRatio].value, this.media.dataset);
        core.bus.trigger('deactivate_snippet');

        this._onDocumentMousedown = this._onDocumentMousedown.bind(this);
        // We use capture so that the handler is called before other editor handlers
        // like save, such that we can restore the src before a save.
        this.document.addEventListener('mousedown', this._onDocumentMousedown, {capture: true});
        return _super(...arguments);
    },
    /**
     * @override
     */
    destroy() {
        if (this.$cropperImage) {
            this.$cropperImage.cropper('destroy');
            this.document.removeEventListener('mousedown', this._onDocumentMousedown, {capture: true});
        }
        this.media.setAttribute('src', this.initialSrc);
        return this._super(...arguments);
    },

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * Updates the DOM image with cropped data and associates required
     * information for a potential future save (where required cropped data
     * attachments will be created).
     *
     * @private
     */
    async _save() {
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
        this.initialSrc = await applyModifications(this.media);
        this.$media.trigger('image_cropped');
        this.destroy();
    },
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
    },
    /**
     * Resets the crop box to prevent it going outside the image.
     *
     * @private
     */
    _resetCropBox() {
        this.$cropperImage.cropper('clear');
        this.$cropperImage.cropper('crop');
    },

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
                return this.destroy();
        }
    },
    /**
     * Discards crop if the user clicks outside of the widget.
     *
     * @private
     * @param {MouseEvent} ev
     */
    _onDocumentMousedown(ev) {
        if (document.body.contains(ev.target) && this.$(ev.target).length === 0) {
            return this.destroy();
        }
    },
    /**
     * Resets the cropbox on zoom to prevent crop box overflowing.
     *
     * @private
     */
    async _onCropZoom() {
        // Wait for the zoom event to be fully processed before reseting.
        await new Promise(res => setTimeout(res, 0));
        this._resetCropBox();
    },
});

return ImageCropWidget;
});
