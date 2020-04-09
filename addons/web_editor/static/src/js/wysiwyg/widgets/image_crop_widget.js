odoo.define('wysiwyg.widgets.ImageCropWidget', function (require) {
'use strict';

const core = require('web.core');
const qweb = core.qweb;
const Widget = require('web.Widget');

const _t = core._t;

const ImageCropWidget = Widget.extend({
    xmlDependencies: ['/web_editor/static/src/xml/wysiwyg.xml'],

    /**
     * @constructor
     */
    init(parent, options, media) {
        this._super(...arguments);
        this.media = media;
        // Needed for editors in iframes.
        this.document = media.ownerDocument;
        this.options = options;
        this.$media = $(media);
        const src = this.media.getAttribute('src').split('?')[0];
        // [0] => template rendering, [1] => data-attribute matching, [2] => passed to cropper
        this.aspectRatioList = [
            [_t("Free"), '0/0', 0],
            ["16:9", '16/9', 16 / 9],
            ["4:3", '4/3', 4 / 3],
            ["1:1", '1/1', 1],
            ["2:3", '2/3', 2 / 3],
        ];
        this.imageData = {
            imageSrc: src,
            // the original src for cropped DB images will be fetched later
            originalSrc: this.$media.data('crop:originalSrc') || src,
            // the mimetype for DB images will be fetched later
            mimetype: this.$media.data('crop:mimetype') || (_.str.endsWith(src, '.png') ? 'image/png' : 'image/jpeg'),
            aspectRatio: this.$media.data('aspectRatio') || '0/0',
            // non-external: base64 or relative path that contains the current host. Probably need a more solid check?
            isExternalImage: src.substr(0, 5) !== 'data:' && src[0] !== '/' && src.indexOf(window.location.host) < 0,
            scaleX: 1,
            scaleY: 1,
        };
    },
    /**
     * @override
     */
    async willStart() {
        await this._super.apply(this, arguments);
        if (this.imageData.isExternalImage) {
            return;
        }

        // Get id, mimetype and originalSrc.
        const {attachment, original} = await this._rpc({
            route: '/web_editor/attachment/get_original',
            params: {
                src: this.imageData.imageSrc
            }
        });
        Object.assign(this.imageData, {id: attachment.id, originalSrc: original.url});
    },
    /**
     * @override
     */
    async start() {
        const _super = this._super.bind(this);
        const topLevel = this.document.getElementById('wrapwrap') || this.document;
        const backdrop = this.document.createElement('div');
        this.backdrop = backdrop;
        backdrop.style = `
            background-color: #8888;
            position: absolute;
            top: 0;
            bottom: 0;
            left: 0;
            right: 0;
            z-index: 1024;
        `;

        const cropperWrapper = this.document.createElement('div');
        this.media.setAttribute('src', this.imageData.originalSrc);
        await new Promise(resolve => this.media.addEventListener('load', resolve, {once: true}));
        const cropperImage = this.document.createElement('img');
        cropperImage.setAttribute('src', this.imageData.originalSrc);
        this.$cropperImage = $(cropperImage);
        [cropperImage.style.width, cropperImage.style.height] = [this.$media.width() + 'px', this.$media.height() + 'px'];
        const $buttons = $(qweb.render('wysiwyg.widgets.crop_buttons', {widget: this}));

        cropperWrapper.appendChild(cropperImage);
        cropperWrapper.appendChild($buttons[0]);
        backdrop.appendChild(cropperWrapper);
        topLevel.appendChild(backdrop);
        cropperWrapper.style.position = 'absolute';
        $(cropperWrapper).offset(this.$media.offset());
        [cropperWrapper.style.marginLeft, cropperWrapper.style.marginTop] = [this.$media.css('padding-left'), this.$media.css('padding-top')];

        $buttons.on('click.crop_options', '[data-action]', this._onCropOptionClick.bind(this));

        const data = this.media.dataset;
        await new Promise(resolve => cropperImage.addEventListener('load', resolve, {once: true}));
        this.$cropperImage.cropper({
            viewMode: 2,
            dragMode: 'move',
            autoCropArea: 1.0,
            aspectRatio: parseFloat(data.aspectRatio),
            data: _.mapObject(_.pick(data, 'x', 'y', 'width', 'height', 'rotate', 'scaleX', 'scaleY'), n => parseFloat(n)),
            // Can't use 0 because it's falsy and the lib will then use its defaults (200x100)
            minContainerWidth: 1,
            minContainerHeight: 1,
        });
        core.bus.trigger('deactivate_snippet');

        this._onOutsideClick = this._onOutsideClick.bind(this);
        // We use capture so that the handler is called before other editor handlers
        // like save, such that we can restore the src before a save.
        this.document.addEventListener('click', this._onOutsideClick, {capture: true});
        return _super(...arguments);
    },
    /**
     * @override
     */
    destroy() {
        this.$cropperImage.cropper('destroy');
        this.backdrop.remove();
        this.document.removeEventListener('click', this._onOutsideClick, {capture: true});
        return this._super(...arguments);
    },
    /**
     * Updates the DOM image with cropped data and associates required
     * information for a potential future save (where required cropped data
     * attachments will be created).
     *
     * @private
     */
    _save() {
        // Mark the media for later creation of required cropped attachments
        this.media.classList.add('o_cropped_img_to_save');

        // Mark the media with the cropping information which is required for
        // a future crop edition
        this.$media.data({
            'crop:resModel': this.options.res_model,
            'crop:resID': this.options.res_id,
            'crop:id': this.imageData.id,
            'crop:mimetype': this.imageData.mimetype,
            'crop:originalSrc': this.imageData.originalSrc,
            'aspectRatio': this.imageData.aspectRatio,
        });

        this.media.dataset.aspectRatio = this.imageData.aspectRatio;
        const cropperData = this.$cropperImage.cropper('getData');
        Object.entries(cropperData).forEach(([key, value]) => {
            this.media.dataset[key] = value;
            $(this.media).data(key, value);
        });

        // Update the media with base64 source for preview before saving
        var canvas = this.$cropperImage.cropper('getCroppedCanvas', {
            width: cropperData.width,
            height: cropperData.height,
        });
        this.media.setAttribute('src', canvas.toDataURL(this.imageData.mimetype));
        this.destroy();
    },
    /**
     * Discards the current crop.
     *
     * @private
     */
    _discard() {
        this.media.setAttribute('src', this.imageData.imageSrc);
        return this.destroy();
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
                this.imageData.aspectRatio = value;
                return this.$cropperImage.cropper('setAspectRatio', value);
            case 'zoom':
            case 'rotate':
            case 'reset':
                this.$cropperImage.cropper(action, value);
                this.imageData.scaleX = this.imageData.scaleY = 1;
                break;
            case 'flip':
                this.imageData[scaleDirection] *= -1;
                return this.$cropperImage.cropper(scaleDirection, this.imageData[scaleDirection]);
            case 'apply':
                return this._save();
            case 'discard':
                return this._discard();
        }
    },
    /**
     * Discards crop if click outside of the widget.
     *
     * @private
     * @param {MouseEvent} ev
     */
    _onOutsideClick(ev) {
        if (!this.backdrop.contains(ev.target)) {
            return this._discard();
        }
    },
});


return ImageCropWidget;
});
