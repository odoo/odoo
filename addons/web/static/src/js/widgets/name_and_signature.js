odoo.define('web.name_and_signature', function (require) {
'use strict';

var core = require('web.core');
var config = require('web.config');
var utils = require('web.utils');
var Widget = require('web.Widget');

var _t = core._t;

/**
 * This widget allows the user to input his name and to draw his signature.
 * Alternatively the signature can also be generated automatically based on
 * the given name and a selected font, or loaded from an image file.
 */
var NameAndSignature = Widget.extend({
    template: 'web.sign_name_and_signature',
    xmlDependencies: ['/web/static/src/xml/name_and_signature.xml'],
    events: {
        // name
        'input .o_web_sign_name_input': '_onInputSignName',
        // signature
        'click .o_web_sign_signature': '_onClickSignature',
        'change .o_web_sign_signature': '_onChangeSignature',
        // draw
        'click .o_web_sign_draw_button': '_onClickSignDrawButton',
        'click .o_web_sign_draw_clear a': '_onClickSignDrawClear',
        // auto
        'click .o_web_sign_auto_button': '_onClickSignAutoButton',
        'click .o_web_sign_auto_select_style a': '_onClickSignAutoSelectStyle',
        'click .o_web_sign_auto_font_selection a': '_onClickSignAutoFontSelection',
        'mouseover .o_web_sign_auto_font_selection a': '_onMouseOverSignAutoFontSelection',
        'touchmove .o_web_sign_auto_font_selection a': '_onTouchStartSignAutoFontSelection',
        // load
        'click .o_web_sign_load_button': '_onClickSignLoadButton',
        'change .o_web_sign_load_file input': '_onChangeSignLoadInput',
    },

    /**
     * Allows options.
     *
     * @constructor
     * @param {Widget} parent
     * @param {Object} [options={}]
     * @param {number} [options.displaySignatureRatio=3.0] - The ratio used when
     *  (re)computing the size of the signature (width = height * ratio)
     * @param {string} [options.defaultName=''] - The default name of
     *  the signer.
     * @param {string} [options.defaultFont=''] - The unique and default
     *  font for auto mode. If empty, all fonts are visible.
     * * @param {string} [options.fontColor='DarkBlue'] - Color of signature
     * (must be a string color)
     * @param {string} [options.noInputName=false] - If set to true,
     *  the user can not enter his name. If there aren't defaultName,
     *  auto mode is hidden.
     * @param {string} [options.mode='draw'] - @see this.setMode
     * @param {string} [options.signatureType='signature'] - The type of
     *  signature used in 'auto' mode. Can be one of the following values:
     *
     *  - 'signature': it will adapt the characters width to fit the whole
     *    text in the image.
     *  - 'initial': it will adapt the space between characters to fill
     *      the image with the text. The text will be the first letter of
     *      every word in the name, separated by dots.
     */
    init: function (parent, options) {
        this._super.apply(this, arguments);
        options = options || {};
        this.htmlId = _.uniqueId();
        this.defaultName = options.defaultName || '';
        this.defaultFont = options.defaultFont || '';
        this.fontColor = options.fontColor || 'DarkBlue';
        this.displaySignatureRatio = options.displaySignatureRatio || 3.0;
        this.signatureType = options.signatureType || 'signature';
        this.signMode = options.mode || 'draw';
        this.noInputName = options.noInputName || false;
        this.currentFont = 0;
        this.drawTimeout = null;
        this.drawPreviewTimeout = null;
    },
    /**
     * Loads the fonts.
     *
     * @override
     */
    willStart: function () {
        var self = this;
        return Promise.all([
            this._super.apply(this, arguments),
            this._rpc({route: '/web/sign/get_fonts/' + self.defaultFont}).then(function (data) {
                self.fonts = data;
            })
        ]);
    },
    /**
     * Finds the DOM elements, initializes the signature area,
     * and focus the name field.
     *
     * @override
     */
    start: function () {
        var self = this;
        // signature and name input
        this.$signatureGroup = this.$('.o_web_sign_signature_group');
        this.$signatureField = this.$('.o_web_sign_signature');
        this.$nameInput = this.$('.o_web_sign_name_input');
        this.$nameInputGroup = this.$('.o_web_sign_name_group');

        // mode selection buttons
        this.$drawButton = this.$('a.o_web_sign_draw_button');
        this.$autoButton = this.$('a.o_web_sign_auto_button');
        this.$loadButton = this.$('a.o_web_sign_load_button');

        // mode: draw
        this.$drawClear = this.$('.o_web_sign_draw_clear');

        // mode: auto
        this.$autoSelectStyle = this.$('.o_web_sign_auto_select_style');
        this.$autoFontSelection = this.$('.o_web_sign_auto_font_selection');
        this.$autoFontList = this.$('.o_web_sign_auto_font_list');
        for (var i in this.fonts) {
            var $img = $('<img/>').addClass('img-fluid');
            var $a = $('<a/>').addClass('btn p-0').append($img).data('fontNb', i);
            this.$autoFontList.append($a);
        }

        // mode: load
        this.$loadFile = this.$('.o_web_sign_load_file');
        this.$loadInvalid = this.$('.o_web_sign_load_invalid');

        if (this.fonts && this.fonts.length < 2) {
            this.$autoSelectStyle.hide();
        }

        if (this.noInputName) {
            if (this.defaultName === "") {
                this.$autoButton.hide();
            }
            this.$nameInputGroup.hide();
        }

        // Resize the signature area if it is resized
        $(window).on('resize.o_web_sign_name_and_signature', _.debounce(function () {
            if (self.isDestroyed()) {
                // May happen since this is debounced
                return;
            }
            self.resizeSignature();
        }, 250));

        return this._super.apply(this, arguments);
    },
    /**
     * @override
     */
    destroy: function () {
        this._super.apply(this, arguments);
        $(window).off('resize.o_web_sign_name_and_signature');
    },

    //----------------------------------------------------------------------
    // Public
    //----------------------------------------------------------------------

    /**
     * Focuses the name.
     */
    focusName: function () {
        // Don't focus on mobile
        if (!config.device.isMobile) {
            this.$nameInput.focus();
        }
    },
    /**
     * Gets the name currently given by the user.
     *
     * @returns {string} name
     */
    getName: function () {
        return this.$nameInput.val();
    },
    /**
     * Gets the signature currently drawn. The data format is that produced
     * natively by Canvas - base64 encoded (likely PNG) bitmap data.
     *
     * @returns {string[]} Array that contains the signature as a bitmap.
     *  The first element is the mimetype, the second element is the data.
     */
    getSignatureImage: function () {
        return this.$signatureField.jSignature('getData', 'image');
    },
    /**
     * Gets the signature currently drawn, in a format ready to be used in
     * an <img/> src attribute.
     *
     * @returns {string} the signature currently drawn, src ready
     */
    getSignatureImageSrc: function () {
        return this.$signatureField.jSignature('getData');
    },
    /**
     * Returns whether the drawing area is currently empty.
     *
     * @returns {boolean} Whether the drawing area is currently empty.
     */
    isSignatureEmpty: function () {
        var signature = this.$signatureField.jSignature('getData');
        return signature && this.emptySignature ? this.emptySignature === signature : true;
    },
    resizeSignature: function() {
        if (!this.$signatureField) {
            return;
        }
        // recompute size based on the current width
        this.$signatureField.css({width: 'unset'});
        const width = this.$signatureField.width();
        const height = parseInt(width / this.displaySignatureRatio);

        // necessary because the lib is adding invisible div with margin
        // signature field too tall without this code
        this.$signatureField.css({
            width: width,
            height: height,
        });
        this.$signatureField.find('canvas').css({
            width: width,
            height: height,
        });
        return {width, height};
    },
    /**
     * (Re)initializes the signature area:
     *  - set the correct width and height of the drawing based on the width
     *      of the container and the ratio option
     *  - empty any previous content
     *  - correctly reset the empty state
     *  - call @see setMode with reset
     *
     * @returns {Deferred}
     */
    resetSignature: function () {
        if (!this.$signatureField) {
            // no action if called before start
            return Promise.reject();
        }

        const {width, height} = this.resizeSignature();

        this.$signatureField
            .empty()
            .jSignature({
                'decor-color': '#D1D0CE',
                'background-color': 'rgba(255,255,255,0)',
                'show-stroke': false,
                'color': this.fontColor,
                'lineWidth': 2,
                'width': width,
                'height': height,
            });
        this.emptySignature = this.$signatureField.jSignature('getData');

        this.setMode(this.signMode, true);

        this.focusName();

        return Promise.resolve();
    },
    /**
     * Changes the signature mode. Toggles the display of the relevant
     * controls and resets the drawing.
     *
     * @param {string} mode - the mode to use. Can be one of the following:
     *  - 'draw': the user draws the signature manually with the mouse
     *  - 'auto': the signature is drawn automatically using a selected font
     *  - 'load': the signature is loaded from an image file
     * @param {boolean} [reset=false] - Set to true to reset the elements
     *  even if the @see mode has not changed. By default nothing happens
     *  if the @see mode is already selected.
     */
    setMode: function (mode, reset) {
        if (reset !== true && mode === this.signMode) {
            // prevent flickering and unnecessary compute
            return;
        }

        this.signMode = mode;

        this.$drawClear.toggleClass('d-none', this.signMode !== 'draw');
        this.$autoSelectStyle.toggleClass('d-none', this.signMode !== 'auto');
        this.$loadFile.toggleClass('d-none', this.signMode !== 'load');

        this.$drawButton.toggleClass('active', this.signMode === 'draw');
        this.$autoButton.toggleClass('active', this.signMode === 'auto');
        this.$loadButton.toggleClass('active', this.signMode === 'load');

        this.$signatureField.jSignature(this.signMode === 'draw' ? 'enable' : 'disable');
        this.$signatureField.jSignature('reset');

        if (this.signMode === 'auto') {
            // draw based on name
            this._drawCurrentName();
        } else {
            // close style dialog
            this.$autoFontSelection.addClass('d-none');
        }

        if (this.signMode !== 'load') {
            // close invalid file alert
            this.$loadInvalid.addClass('d-none');
        }
    },
    /**
     * Gets the current name and signature, validates them, and returns
     * the result. If they are invalid, displays the errors to the user.
     *
     * @returns {boolean} whether the current name and signature are valid
     */
    validateSignature: function () {
        var name = this.getName();
        var isSignatureEmpty = this.isSignatureEmpty();
        this.$nameInput.parent().toggleClass('o_has_error', !name)
            .find('.form-control, .custom-select').toggleClass('is-invalid', !name);
        this.$signatureGroup.toggleClass('border-danger', isSignatureEmpty);
        return name && !isSignatureEmpty;
    },

    //----------------------------------------------------------------------
    // Private
    //----------------------------------------------------------------------

    /**
     * Draws the current name with the current font in the signature field.
     *
     * @private
     */
    _drawCurrentName: function () {
        var font = this.fonts[this.currentFont];
        var text = this._getCleanedName();
        var canvas = this.$signatureField.find('canvas')[0];
        var img = this._getSVGText(font, text, canvas.width, canvas.height);
        return this._printImage(img);
    },
    /**
     * Returns the given name after cleaning it by removing characters that
     * are not supposed to be used in a signature. If @see signatureType is set
     * to 'initial', returns the first letter of each word, separated by dots.
     *
     * @private
     * @returns {string} cleaned name
     */
    _getCleanedName: function () {
        var text = this.getName();
        if (this.signatureType === 'initial') {
            return (text.split(' ').map(function (w) {
                return w[0];
            }).join('.') + '.');
        }
        return text;
    },
    /**
     * Gets an SVG matching the given parameters, output compatible with the
     * src attribute of <img/>.
     *
     * @private
     * @param {string} font: base64 encoded font to use
     * @param {string} text: the name to draw
     * @param {number} width: the width of the resulting image in px
     * @param {number} height: the height of the resulting image in px
     * @returns {string} image = mimetype + image data
     */
    _getSVGText: function (font, text, width, height) {
        var $svg = $(core.qweb.render('web.sign_svg_text', {
            width: width,
            height: height,
            font: font,
            text: text,
            type: this.signatureType,
            color: this.fontColor,
        }));
        $svg.attr({
            'xmlns': "http://www.w3.org/2000/svg",
            'xmlns:xlink': "http://www.w3.org/1999/xlink",
        });

        return "data:image/svg+xml," + encodeURI($svg[0].outerHTML);
    },
    /**
     * Displays the given image in the signature field.
     * If needed, resizes the image to fit the existing area.
     *
     * @private
     * @param {string} imgSrc - data of the image to display
     */
    _printImage: function (imgSrc) {
        var self = this;

        var image = new Image;
        image.onload = function () {
            // don't slow down the UI if the drawing is slow, and prevent
            // drawing twice when calling this method in rapid succession
            clearTimeout(self.drawTimeout);
            self.drawTimeout = setTimeout(function () {
                var width = 0;
                var height = 0;
                var ratio = image.width / image.height;

                var $canvas = self.$signatureField.find('canvas');
                var context = $canvas[0].getContext('2d');

                if (image.width / $canvas[0].width > image.height / $canvas[0].height) {
                    width = $canvas[0].width;
                    height = parseInt(width / ratio);
                } else {
                    height = $canvas[0].height;
                    width = parseInt(height * ratio);
                }
                self.$signatureField.jSignature('reset');
                var ignoredContext = _.pick(context, ['shadowOffsetX', 'shadowOffsetY']);
                _.extend(context, {shadowOffsetX: 0, shadowOffsetY: 0});
                context.drawImage(image,
                    0,
                    0,
                    image.width,
                    image.height,
                    ($canvas[0].width - width) / 2,
                    ($canvas[0].height - height) / 2,
                    width,
                    height
                );
                _.extend(context, ignoredContext);
                self.trigger_up('signature_changed');
            }, 0);
        };
        image.src = imgSrc;
    },
    /**
     * Sets the font to use in @see mode 'auto'. Redraws the signature if
     * the font has been changed.
     *
     * @private
     * @param {number} index - index of the font in @see this.fonts
     */
    _setFont: function (index) {
        if (index !== this.currentFont) {
            this.currentFont = index;
            this._drawCurrentName();
        }
    },
    /**
     * Updates the preview buttons by rendering the signature for each font.
     *
     * @private
     */
    _updatePreviewButtons: function () {
        var self = this;
        // don't slow down the UI if the drawing is slow, and prevent
        // drawing twice when calling this method in rapid succession
        clearTimeout(this.drawPreviewTimeout);
        this.drawPreviewTimeout = setTimeout(function () {
            var height = 100;
            var width = parseInt(height * self.displaySignatureRatio);
            var $existingButtons = self.$autoFontList.find('a');
            for (var i = 0; i < self.fonts.length; i++) {
                var imgSrc = self._getSVGText(
                    self.fonts[i],
                    self._getCleanedName() || _t("Your name"),
                    width,
                    height
                );
                $existingButtons.eq(i).find('img').attr('src', imgSrc);
            }
        }, 0);
    },
    /**
     * Waits for the signature to be not empty and triggers up the event
     * `signature_changed`.
     * This is necessary because some methods of jSignature are async but
     * they don't return a promise and don't trigger any event.
     *
     * @private
     * @param {Deferred} [def=Deferred] - Deferred that will be returned by
     *  the method and resolved when the signature is not empty anymore.
     * @returns {Deferred}
     */
    _waitForSignatureNotEmpty: function (def) {
        def = def || $.Deferred();
        if (!this.isSignatureEmpty()) {
            this.trigger_up('signature_changed');
            def.resolve();
        } else {
            // Use the existing def to prevent the method from creating a new
            // one at every loop.
            setTimeout(this._waitForSignatureNotEmpty.bind(this, def), 10);
        }
        return def;
    },

    //----------------------------------------------------------------------
    // Handlers
    //----------------------------------------------------------------------

    /**
     * Handles click on the signature: closes the font selection.
     *
     * @see mode 'auto'
     * @private
     * @param {Event} ev
     */
    _onClickSignature: function (ev) {
        this.$autoFontSelection.addClass('d-none');
    },
    /**
     * Handles click on the Auto button: activates @see mode 'auto'.
     *
     * @private
     * @param {Event} ev
     */
    _onClickSignAutoButton: function (ev) {
        ev.preventDefault();
        this.setMode('auto');
    },
    /**
     * Handles click on a font: uses it and closes the font selection.
     *
     * @see mode 'auto'
     * @private
     * @param {Event} ev
     */
    _onClickSignAutoFontSelection: function (ev) {
        this.$autoFontSelection.addClass('d-none').removeClass('d-flex').css('width', 0);
        this._setFont(parseInt($(ev.currentTarget).data('font-nb')));
    },
    /**
     * Handles click on Select Style: opens and updates the font selection.
     *
     * @see mode 'auto'
     * @private
     * @param {Event} ev
     */
    _onClickSignAutoSelectStyle: function (ev) {
        var self = this;
        var width = Math.min(
            self.$autoFontSelection.find('a').first().height() * self.displaySignatureRatio * 1.25,
            this.$signatureField.width()
        );

        ev.preventDefault();
        self._updatePreviewButtons();

        this.$autoFontSelection.removeClass('d-none').addClass('d-flex');
        this.$autoFontSelection.show().animate({'width': width}, 500, function () {});
    },
    /**
     * Handles click on the Draw button: activates @see mode 'draw'.
     *
     * @private
     * @param {Event} ev
     */
    _onClickSignDrawButton: function (ev) {
        ev.preventDefault();
        this.setMode('draw');
    },
    /**
     * Handles click on clear: empties the signature field.
     *
     * @see mode 'draw'
     * @private
     * @param {Event} ev
     */
    _onClickSignDrawClear: function (ev) {
        ev.preventDefault();
        this.$signatureField.jSignature('reset');
    },
    /**
     * Handles click on the Load button: activates @see mode 'load'.
     *
     * @private
     * @param {Event} ev
     */
    _onClickSignLoadButton: function (ev) {
        ev.preventDefault();
        // open file upload automatically (saves 1 click)
        this.$loadFile.find('input').click();
        this.setMode('load');
    },
    /**
     * Triggers up the signature change event.
     *
     * @private
     * @param {Event} ev
     */
    _onChangeSignature: function (ev) {
        this.trigger_up('signature_changed');
    },
    /**
     * Handles change on load file input: displays the loaded image if the
     * format is correct, or diplays an error otherwise.
     *
     * @see mode 'load'
     * @private
     * @param {Event} ev
     * @return bool|undefined
     */
    _onChangeSignLoadInput: function (ev) {
        var self = this;
        var f = ev.target.files[0];
        if (f === undefined) {
            return false;
        }
        if (f.type.substr(0, 5) !== 'image') {
            this.$signatureField.jSignature('reset');
            this.$loadInvalid.removeClass('d-none');
            return false;
        }
        this.$loadInvalid.addClass('d-none');

        utils.getDataURLFromFile(f).then(function (result) {
            self._printImage(result);
        });
    },
    /**
     * Handles input on name field: if the @see mode is 'auto', redraws the
     * signature with the new name. Also updates the font selection if open.
     *
     * @private
     * @param {Event} ev
     */
    _onInputSignName: function (ev) {
        if (this.signMode !== 'auto') {
            return;
        }
        this._drawCurrentName();
        if (!this.$autoFontSelection.hasClass('d-none')) {
            this._updatePreviewButtons();
        }
    },
    /**
     * Handles mouse over on font selection: uses this font.
     *
     * @see mode 'auto'
     * @private
     * @param {Event} ev
     */
    _onMouseOverSignAutoFontSelection: function (ev) {
        this._setFont(parseInt($(ev.currentTarget).data('font-nb')));
    },
    /**
     * Handles touch start on font selection: uses this font.
     *
     * @see mode 'auto'
     * @private
     * @param {Event} ev
     */
    _onTouchStartSignAutoFontSelection: function (ev) {
        this._setFont(parseInt($(ev.currentTarget).data('font-nb')));
    },
});

return {
    NameAndSignature: NameAndSignature,
};
});
