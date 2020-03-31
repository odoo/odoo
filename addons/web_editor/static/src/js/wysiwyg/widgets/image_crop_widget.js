odoo.define('wysiwyg.widgets.ImageCropWidget', function (require) {
'use strict';

const core = require('web.core');
const qweb = core.qweb;
const Widget = require('web.Widget');

const _t = core._t;

// Fields returned by cropper lib 'getData' method
const cropperDataFields = ['x', 'y', 'width', 'height', 'rotate', 'scaleX', 'scaleY'];
const ImageCropWidget = Widget.extend({
    template: ['wysiwyg.widgets.crop'],
    xmlDependencies: ['/web_editor/static/src/xml/wysiwyg.xml'],
    events: {
        'click.crop_options [data-action]': '_onCropOptionClick',
        // zoom event is triggered by the cropperjs library when the user zooms.
        'zoom': '_onCropZoom',
    },
    // Crop attributes that are saved with the DOM. Should only be removed when the image is changed.
    persistentAttributes: [
        ...cropperDataFields,
        'aspectRatio',
    ],
    // Attributes that are used to keep data from one crop to the next in the same session
    // If present, should be used by the cropper instead of querying db
    sessionAttributes: [
        'attachmentId',
        'originalSrc',
        'originalId',
        'originalName',
        'mimetype',
    ],
    // Attributes that are used by saveCroppedImages to create or update attachments
    saveAttributes: [
        'resModel',
        'resId',
        'attachmentId',
        'originalId',
        'originalName',
        'mimetype',
    ],

    /**
     * @constructor
     */
    init(parent, options, media) {
        this._super(...arguments);
        this.media = media;
        this.$media = $(media);
        // Needed for editors in iframes.
        this.document = media.ownerDocument;
        // Used for res_model and res_id
        this.options = options;
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
        this.isCroppable = src.startsWith('data:') || new URL(src, window.location.origin).origin === window.location.origin;
    },
    /**
     * @override
     */
    async willStart() {
        await this._super.apply(this, arguments);
        if (!this.isCroppable) {
            return;
        }
        // If there is a marked originalSrc, a previous crop has already happened,
        // we won't find the original from the data-url. Reuse the data from the previous crop.
        if (this.media.dataset.originalSrc) {
            this.sessionAttributes.forEach(attr => {
                this[attr] = this.media.dataset[attr];
            });
            return;
        }

        // Get id, mimetype and originalSrc.
        const {attachment, original} = await this._rpc({
            route: '/web_editor/get_image_info',
            params: {src: this.initialSrc.split(/[?#]/)[0]},
        });
        if (!attachment) {
            // Local image that doesn't have an attachment, don't allow crop?
            // In practice, this can happen if an image is directly linked with its
            // static url and there is no corresponding attachment, (eg, logo in mass_mailing)
            this.isCroppable = false;
            return;
        }
        this.originalId = original.id;
        this.originalSrc = original.image_src;
        this.originalName = original.name;
        this.mimetype = original.mimetype;
        this.attachmentId = attachment.id;
    },
    /**
     * @override
     */
    async start() {
        if (!this.isCroppable) {
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
        this.media.setAttribute('src', this.originalSrc);
        await new Promise(resolve => this.media.addEventListener('load', resolve, {once: true}));
        this.$cropperImage = this.$('.o_we_cropper_img');
        const cropperImage = this.$cropperImage[0];
        [cropperImage.style.width, cropperImage.style.height] = [this.$media.width() + 'px', this.$media.height() + 'px'];

        // Overlaying the cropper image over the real image
        const offset = this.$media.offset();
        offset.left += parseInt(this.$media.css('padding-left'));
        offset.top += parseInt(this.$media.css('padding-right'));
        $cropperWrapper.offset(offset);

        cropperImage.setAttribute('src', this.originalSrc);
        await new Promise(resolve => cropperImage.addEventListener('load', resolve, {once: true}));
        this.$cropperImage.cropper({
            viewMode: 2,
            dragMode: 'move',
            autoCropArea: 1.0,
            aspectRatio: this.aspectRatios[this.aspectRatio].value,
            data: _.mapObject(_.pick(this.media.dataset, ...cropperDataFields), value => parseFloat(value)),
            // Can't use 0 because it's falsy and the lib will then use its defaults (200x100)
            minContainerWidth: 1,
            minContainerHeight: 1,
        });
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
    _save() {
        // Mark the media for later creation/update of cropped attachment
        this.media.classList.add('o_cropped_img_to_save');

        this.allAttributes.forEach(attr => {
            delete this.media.dataset[attr];
            const value = this._getAttributeValue(attr);
            if (value) {
                this.media.dataset[attr] = value;
            }
        });

        // Update the media with base64 source for preview before saving
        const cropperData = this.$cropperImage.cropper('getData');
        const canvas = this.$cropperImage.cropper('getCroppedCanvas', {
            width: cropperData.width,
            height: cropperData.height,
        });
        // 1 is the quality if the image is jpeg (in the range O-1), defaults to .92
        this.initialSrc = canvas.toDataURL(this.mimetype, 1);
        // src will be set to this.initialSrc in the destroy method
        this.destroy();
    },
    /**
     * Returns an attribute's value for saving.
     *
     * @private
     */
    _getAttributeValue(attr) {
        switch (attr) {
            case 'resModel':
                return this.options.res_model;
            case 'resId':
                return this.options.res_id;
        }
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

const proto = ImageCropWidget.prototype;
proto.allAttributes = [...new Set([
    ...proto.persistentAttributes,
    ...proto.sessionAttributes,
    ...proto.saveAttributes,
])];
proto.removeOnSaveAttributes = [...new Set([
    ...proto.sessionAttributes,
    ...proto.saveAttributes,
])];

return ImageCropWidget;
});
