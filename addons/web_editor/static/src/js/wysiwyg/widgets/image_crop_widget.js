odoo.define('wysiwyg.widgets.CropImageDialog', function (require) {
'use strict';

var core = require('web.core');
var Dialog = require('wysiwyg.widgets.Dialog');

var _t = core._t;

/**
 * CropImageDialog widget. Let users crop an image.
 */
var CropImageDialog = Dialog.extend({
    template: 'wysiwyg.widgets.crop_image',
    xmlDependencies: Dialog.prototype.xmlDependencies.concat(
        ['/web_editor/static/src/xml/wysiwyg.xml']
    ),
    events: _.extend({}, Dialog.prototype.events, {
        'click .o_crop_options [data-event]': '_onCropOptionClick',
    }),

    /**
     * @constructor
     */
    init: function (parent, options, media) {
        var self = this;
        this.media = media;
        this.$media = $(this.media);
        var src = this.$media.attr('src').split('?')[0];
        this.aspectRatioList = [
            [_t("Free"), '0/0', 0],
            ["16:9", '16/9', 16 / 9],
            ["4:3", '4/3', 4 / 3],
            ["1:1", '1/1', 1],
            ["2:3", '2/3', 2 / 3],
        ];
        this.imageData = {
            imageSrc: src,
            originalSrc: this.$media.data('crop:originalSrc') || src, // the original src for cropped DB images will be fetched later
            mimetype: this.$media.data('crop:mimetype') || (_.str.endsWith(src, '.png') ? 'image/png' : 'image/jpeg'), // the mimetype for DB images will be fetched later
            aspectRatio: this.$media.data('aspectRatio') || this.aspectRatioList[0][1],
            isExternalImage: src.substr(0, 5) !== 'data:' && src[0] !== '/' && src.indexOf(window.location.host) < 0,
        };
        this.options = _.extend({
            title: _t("Crop Image"),
            buttons: this.imageData.isExternalImage ? [{
                text: _t("Close"),
                close: true,
            }] : [{
                text: _t("Save"),
                classes: 'btn-primary',
                click: this.save,
            }, {
                text: _t("Discard"),
                close: true,
            }],
        }, options || {});
        this._super(parent, this.options);
        this.trigger_up('getRecordInfo', _.extend(this.options, {
            callback: function (recordInfo) {
                _.defaults(self.options, recordInfo);
            },
        }));
    },
    /**
     * @override
     */
    willStart: function () {
        var self = this;
        var def = this._super.apply(this, arguments);
        if (this.imageData.isExternalImage) {
            return def;
        }

        var defs = [def];
        var params = {};
        var isDBImage = false;
        var matchImageID = this.imageData.imageSrc.match(/^\/web\/image\/(\d+)/);
        if (matchImageID) {
            params.image_id = parseInt(matchImageID[1]);
            isDBImage = true;
        } else {
            var matchXmlID = this.imageData.imageSrc.match(/^\/web\/image\/([^/?]+)/);
            if (matchXmlID) {
                params.xml_id = matchXmlID[1];
                isDBImage = true;
            }
        }
        if (isDBImage) {
            defs.push(this._rpc({
                route: '/web_editor/get_image_info',
                params: params,
            }).then(function (res) {
                _.extend(self.imageData, res);
            }));
        }
        return Promise.all(defs);
    },
    /**
     * @override
     */
    start: function () {
        this.$cropperImage = this.$('.o_cropper_image');
        if (this.$cropperImage.length) {
            var data = this.$media.data();
            var ratio = 0;
            for (var i = 0; i < this.aspectRatioList.length; i++) {
                if (this.aspectRatioList[i][1] === data.aspectRatio) {
                    ratio = this.aspectRatioList[i][2];
                    break;
                }
            }
            this.$cropperImage.cropper({
                viewMode: 2,
                dragMode: 'move',
                autoCropArea: 1.0,
                aspectRatio: ratio,
                data: _.pick(data, 'x', 'y', 'width', 'height', 'rotate', 'scaleX', 'scaleY')
            });
        }
        return this._super.apply(this, arguments);
    },
    /**
     * @override
     */
    destroy: function () {
        if (this.$cropperImage.length) {
            this.$cropperImage.cropper('destroy');
        }
        this._super.apply(this, arguments);
    },
    /**
     * Updates the DOM image with cropped data and associates required
     * information for a potential future save (where required cropped data
     * attachments will be created).
     *
     * @override
     */
    save: function () {
        var self = this;
        var cropperData = this.$cropperImage.cropper('getData');

        // Mark the media for later creation of required cropped attachments...
        this.$media.addClass('o_cropped_img_to_save');

        // ... and attach required data
        this.$media.data('crop:resModel', this.options.res_model);
        this.$media.data('crop:resID', this.options.res_id);
        this.$media.data('crop:id', this.imageData.id);
        this.$media.data('crop:mimetype', this.imageData.mimetype);
        this.$media.data('crop:originalSrc', this.imageData.originalSrc);

        // Mark the media with the cropping information which is required for
        // a future crop edition
        this.$media
            .attr('data-aspect-ratio', this.imageData.aspectRatio)
            .data('aspectRatio', this.imageData.aspectRatio);
        _.each(cropperData, function (value, key) {
            key = _.str.dasherize(key);
            self.$media.attr('data-' + key, value);
            self.$media.data(key, value);
        });

        // Update the media with base64 source for preview before saving
        var canvas = this.$cropperImage.cropper('getCroppedCanvas', {
            width: cropperData.width,
            height: cropperData.height,
        });
        this.$media.attr('src', canvas.toDataURL(this.imageData.mimetype));

        this.final_data = this.media;
        return this._super.apply(this, arguments);
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
    _onCropOptionClick: function (ev) {
        var $option = $(ev.currentTarget);
        var opt = $option.data('event');
        var value = $option.data('value');
        switch (opt) {
            case 'ratio':
                this.$cropperImage.cropper('reset');
                this.imageData.aspectRatio = $option.data('label');
                this.$cropperImage.cropper('setAspectRatio', value);
                break;
            case 'zoom':
            case 'rotate':
            case 'reset':
                this.$cropperImage.cropper(opt, value);
                break;
            case 'flip':
                var direction = value === 'horizontal' ? 'x' : 'y';
                var scaleAngle = -$option.data(direction);
                $option.data(direction, scaleAngle);
                this.$cropperImage.cropper('scale' + direction.toUpperCase(), scaleAngle);
                break;
        }
    },
});


return CropImageDialog;
});
