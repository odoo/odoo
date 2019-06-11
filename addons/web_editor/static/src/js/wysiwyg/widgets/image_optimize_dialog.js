odoo.define('wysiwyg.widgets.image_optimize_dialog', function (require) {
'use strict';

var core = require('web.core');
var Dialog = require('web.Dialog');

var _t = core._t;

var ImageOptimizeDialog = Dialog.extend({
    template: 'wysiwyg.widgets.image.optimize',
    xmlDependencies: (Dialog.prototype.xmlDependencies || []).concat([
        '/web_editor/static/src/xml/wysiwyg.xml',
    ]),
    events: _.extend({}, Dialog.prototype.events, {
        'click .o_we_width_preset': '_onWidthPresetClick',
        'input #o_we_height': '_onHeightInput',
        'input #o_we_name_input': '_onNameInput',
        'input #o_we_optimize_quality': '_onOptimizeQualityInput',
        'input #o_we_quality_input': '_onQualityInput',
        'input #o_we_width': '_onWidthInput',
        'input .o_we_quality_range': '_onQualityRangeInput',
    }),

    /**
     * @constructor
     */
    init: function (parent, params, options) {
        this._super(parent, _.extend({}, {
            title: _t("Improve your Image"),
            size: 'large',
            buttons: [
                {text: _t("Optimize"), classes: 'btn-primary o_we_save', close: false, click: this._onOptimizeClick.bind(this)},
                {text: _t("Keep Original"), close: false, click: this._onKeepOriginalClick.bind(this)}
            ],
        }, options));

        this.isExisting = params.isExisting;
        this.attachment = params.attachment;
        // We do not support resizing and quality for:
        //  - SVG because it doesn't make sense
        //  - GIF because our current code is not made to handle all the frames
        this.disableResize = ['image/jpeg', 'image/jpe', 'image/jpg', 'image/png'].indexOf(this.attachment.mimetype) === -1;
        this.disableQuality = this.disableResize;
        this.toggleQuality = this.attachment.mimetype === 'image/png';
        this.optimizedWidth = Math.min(params.optimizedWidth || this.attachment.image_width, this.attachment.image_width);
        this.defaultQuality = this.isExisting ? 100 : 80;
        this.defaultWidth = parseInt(this.isExisting ? this.attachment.image_width : this.optimizedWidth);
        this.defaultHeight = parseInt(this.isExisting || !this.attachment.image_width ? this.attachment.image_height :
            this.optimizedWidth / this.attachment.image_width * this.attachment.image_height);

        this.suggestedWidths = [];
        this._addSuggestedWidth(128, '128');
        this._addSuggestedWidth(256, '256');
        this._addSuggestedWidth(512, '512');
        this._addSuggestedWidth(1024, '1024');
        this._addSuggestedWidth(this.optimizedWidth,
            _.str.sprintf(_t("%d (Suggested)"), this.optimizedWidth));
        this.suggestedWidths.push({
            'width': this.attachment.image_width,
            'text': _.str.sprintf(_t("%d (Original)"), this.attachment.image_width),
        });
        this.suggestedWidths = _.sortBy(this.suggestedWidths, 'width');
        this._updatePreview = _.debounce(this._updatePreview.bind(this), 300);
    },
    /**
     * @override
     */
    start: function () {
        var self = this;
        var promise = this._super.apply(this, arguments);
        this.$nameInput = this.$('#o_we_name_input');
        this.$previewImage = this.$('.o_we_preview_image');
        this.$saveButton = this.$footer.find('.o_we_save');

        // The following selectors might not contain anything:
        // - depending on disableResize
        this.$widthPresets = this.$('.o_we_width_preset');
        this.$widthInput = this.$('#o_we_width');
        this.$heightInput = this.$('#o_we_height');
        // - depending on disableQuality
        this.$qualityRange = this.$('.o_we_quality_range');
        this.$qualityInput = this.$('#o_we_quality_input');
        // - depending on toggleQuality
        this.$qualityCheckBox = this.$('#o_we_optimize_quality');

        this._updatePreview();
        this._validateForm();
        this.opened().then(function () {
            self.$nameInput.focus();
        });
        return promise;
    },

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * Adds a size to the list of suggested width, only if it is smaller than
     * the image width (we don't scale up images).
     *
     * @private
     * @param {number} size: integer
     * @param {string} text
     */
    _addSuggestedWidth: function (size, text) {
        if (size < this.attachment.image_width) {
            this.suggestedWidths.push({
                width: size,
                text: text,
            });
        }
    },
    /**
     * Gets the current quality from the input, adapts it to match what is
     * expected by image tools, and returns it.
     *
     * The adaptation consists of transforming the quality 100 to 0 to disable
     * optimizations, and to convert values between 95 and 99 to 95 because
     * values above 95 results in large files with hardly any gain in image
     * quality.
     *
     * See `quality` parameter at:
     * https://pillow.readthedocs.io/en/4.0.x/handbook/image-file-formats.html#jpeg
     *
     * @private
     * @returns {number} the quality as integer
     */
    _getAdaptedQuality: function () {
        var quality = 0;
        if (this.$qualityCheckBox.length) {
            if (this.$qualityCheckBox.is(":checked")) {
                // any value will do, as long as it is not 100 or falsy
                quality = 50;
            }
        } else if (this.$qualityRange.length) {
            quality = parseInt(this.$qualityRange.val() || 0);
        }
        if (quality === 100) {
            quality = 0;
        }
        return Math.min(95, quality);
    },
    /**
     * Updates the preview to match the current settings, and also highlights
     * the width preset buttons if applicable.
     *
     * @private
     */
    _updatePreview: function () {
        if (!this._validatePreview()) {
            return;
        }
        var width = parseInt(this.$widthInput.val() || 0);
        var height = parseInt(this.$heightInput.val() || 0);
        this.$previewImage.attr('src', _.str.sprintf('/web/image/%d/%dx%d?quality=%d',
            this.attachment.id, width, height, this._getAdaptedQuality()));
        this.$widthPresets.removeClass('active');
        _.each(this.$widthPresets, function (button) {
            var $button = $(button);
            if (parseInt($button.data('width')) === width) {
                $button.addClass('active');
            }
        });
    },
    /**
     * Validates the form and toggles the save button accordingly.
     *
     * @private
     * @returns {boolean} whether the form is valid
     */
    _validateForm: function () {
        var name = this.$nameInput.val();
        var isValid = name && this._validatePreview();
        this.$saveButton.prop('disabled', !isValid);
        return isValid;
    },
    /**
     * Validates the preview values.
     *
     * @private
     * @returns {boolean} whether the preview values are valid
     */
    _validatePreview: function () {
        var isValid = true;
        var quality = this._getAdaptedQuality();
        var width = parseInt(this.$widthInput.val() || 0);
        var height = parseInt(this.$heightInput.val() || 0);
        if (quality < 0 || quality > 100) {
            isValid = false;
        }
        if (width < 0 || width > this.attachment.image_width) {
            isValid = false;
        }
        if (height < 0 || height > this.attachment.image_height) {
            isValid = false;
        }
        return isValid;
    },

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    /**
     * @private
     */
    _onHeightInput: function () {
        var height = parseInt(this.$heightInput.val()) || 0;
        this.$widthInput
            .val(parseInt(height / this.attachment.image_height * this.attachment.image_width));
        this._updatePreview();
        this._validateForm();
    },
    /**
     * @private
     */
    _onKeepOriginalClick: function () {
        if (!this.isExisting) {
            this.trigger_up('attachment_updated', this.attachment);
        }
        this.close();
    },
    /**
     * @private
     */
    _onNameInput: function () {
        this._validateForm();
    },
    /**
     * Handles clicking on the save button: updates the given attachment with
     * the selected settings and triggers up the `attachment_updated`` event,
     * then closes the dialog.
     *
     * @private
     * @returns {Promise}
     */
    _onOptimizeClick: function () {
        var self = this;
        var name = this.$nameInput.val();
        var params = {
            'name': name,
            'quality': this._getAdaptedQuality(),
            'width': parseInt(this.$widthInput.val() || 0),
            'height': parseInt(this.$heightInput.val() || 0),
        };
        if (this.isExisting) {
            params['copy'] = true;
        }
        return this._rpc({
            route: _.str.sprintf('/web_editor/attachment/%d/update', this.attachment.id),
            params: params,
        }).then(function (attachment) {
            self.trigger_up('attachment_updated', attachment);
            self.close();
        });
    },
    /**
     * @private
     */
    _onQualityInput: function () {
        var quality = parseInt(this.$qualityInput.val() || 0);
        // adapt the quality to what will actually happen
        if (quality === 0) {
            quality = 100;
        }
        // prevent flickering when clearing the input to type something else
        if (!quality) {
            return;
        }
        this.$qualityRange.val(quality);
        this._onQualityRangeInput();
    },
    /**
     * @private
     */
    _onQualityRangeInput: function () {
        var quality = parseInt(this.$qualityRange.val() || 0);
        this.$qualityInput.val(quality);
        this._updatePreview();
        this._validateForm();
    },
    /**
     * @private
     */
    _onOptimizeQualityInput: function () {
        this._updatePreview();
    },
    /**
     * @private
     */
    _onWidthInput: function () {
        var width = parseInt(this.$widthInput.val() || 0);
        this.$heightInput
            .val(parseInt(width / this.attachment.image_width * this.attachment.image_height));
        this._updatePreview();
        this._validateForm();
    },
    /**
     * @private
     */
    _onWidthPresetClick: function (ev) {
        ev.preventDefault();
        this.$widthInput.val(parseInt($(ev.target).data('width')));
        this._onWidthInput();
    },
});

return {
    ImageOptimizeDialog: ImageOptimizeDialog,
};
});
