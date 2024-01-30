odoo.define('web.Colorpicker', function (require) {
'use strict';

var core = require('web.core');
var utils = require('web.utils');
var Dialog = require('web.Dialog');
var Widget = require('web.Widget');

var _t = core._t;

var ColorpickerWidget = Widget.extend({
    template: 'Colorpicker',
    events: {
        'click': '_onClick',
        'keypress': '_onKeypress',
        'mousedown .o_color_pick_area': '_onMouseDownPicker',
        'mousedown .o_color_slider': '_onMouseDownSlider',
        'mousedown .o_opacity_slider': '_onMouseDownOpacitySlider',
        'change .o_color_picker_inputs': '_onChangeInputs',
    },

    /**
     * @constructor
     * @param {Widget} parent
     * @param {Object} [options]
     * @param {string} [options.defaultColor='#FF0000']
     * @param {string} [options.noTransparency=false]
     * @param {boolean} [options.stopClickPropagation=false]
     */
    init: function (parent, options) {
        this._super(...arguments);
        options = options || {};

        this.pickerFlag = false;
        this.sliderFlag = false;
        this.opacitySliderFlag = false;
        this.colorComponents = {};
        this.uniqueId = _.uniqueId('colorpicker');
        this.selectedHexValue = '';

        // Need to be bound on all documents to work in all possible cases (we
        // have to be able to start dragging/moving from the colorpicker to
        // anywhere on the screen, crossing iframes).
        // TODO adapt in master: these events should probably be bound in
        // `start` instead of `init` (at least to be more conventional).
        this.$documents = $([window.top, ...Array.from(window.top.frames).filter(frame => {
            try {
                const document = frame.document;
                return !!document;
            } catch {
                // We cannot access the document (cross origin).
                return false;
            }
        })].map(w => w.document));
        this.$documents.on(`mousemove.${this.uniqueId}`, _.throttle((ev) => {
            this._onMouseMovePicker(ev);
            this._onMouseMoveSlider(ev);
            this._onMouseMoveOpacitySlider(ev);
        }, 50));
        this.$documents.on(`mouseup.${this.uniqueId}`, _.throttle((ev) => {
            if (this.pickerFlag || this.sliderFlag || this.opacitySliderFlag) {
                this._colorSelected();
            }
            this.pickerFlag = false;
            this.sliderFlag = false;
            this.opacitySliderFlag = false;
        }, 10));

        this.options = _.clone(options);
    },
    /**
     * @override
     */
    start: function () {
        this.$colorpickerArea = this.$('.o_color_pick_area');
        this.$colorpickerPointer = this.$('.o_picker_pointer');
        this.$colorSlider = this.$('.o_color_slider');
        this.$colorSliderPointer = this.$('.o_slider_pointer');
        this.$opacitySlider = this.$('.o_opacity_slider');
        this.$opacitySliderPointer = this.$('.o_opacity_pointer');

        var defaultColor = this.options.defaultColor || '#FF0000';
        var rgba = ColorpickerWidget.convertCSSColorToRgba(defaultColor);
        if (rgba) {
            this._updateRgba(rgba.red, rgba.green, rgba.blue, rgba.opacity);
        }

        // Pre-fill the inputs. This is because on safari, the baseline for empty
        // input is not the baseline of where the text would be, but the bottom
        // of the input itself. (see https://bugs.webkit.org/show_bug.cgi?id=142968)
        // This will cause the first _updateUI to alter the layout of the colorpicker
        // which will change its height. Changing the height of an element inside of
        // the callback to a ResizeObserver observing it will cause an error
        // (ResizeObserver loop completed with undelivered notifications) that cannot
        // be caught, which will open the crash manager. Prefilling the inputs sets
        // the baseline correctly from the start so the layout doesn't change.
        Object.entries(this.colorComponents).forEach(([component, value]) => {
            const input = this.el.querySelector(`.o_${component}_input`);
            if (input) {
                input.value = value;
            }
        });
        const resizeObserver = new window.ResizeObserver(() => {
            this._updateUI();
        });
        resizeObserver.observe(this.el);

        this.previewActive = true;
        return this._super.apply(this, arguments);
    },
    /**
     * @override
     */
    destroy: function () {
        this._super.apply(this, arguments);
        this.$documents.off(`.${this.uniqueId}`);
    },
    /**
     * Sets the currently selected color
     *
     * @param {string} color rgb[a]
     */
    setSelectedColor: function (color) {
        var rgba = ColorpickerWidget.convertCSSColorToRgba(color);
        if (rgba) {
            const oldPreviewActive = this.previewActive;
            this.previewActive = false;
            this._updateRgba(rgba.red, rgba.green, rgba.blue, rgba.opacity);
            this.previewActive = oldPreviewActive;
            this._updateUI();
        }
    },

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * Updates input values, color preview, picker and slider pointer positions.
     *
     * @private
     */
    _updateUI: function () {
        var self = this;

        // Update inputs
        _.each(this.colorComponents, function (value, color) {
            self.$(_.str.sprintf('.o_%s_input', color)).val(value);
        });

        // Update preview
        this.$('.o_color_preview').css('background-color', this.colorComponents.cssColor);

        // Update picker area and picker pointer position
        this.$colorpickerArea.css('background-color', _.str.sprintf('hsl(%s, 100%%, 50%%)', this.colorComponents.hue));
        var top = (100 - this.colorComponents.lightness) * this.$colorpickerArea.height() / 100;
        var left = this.colorComponents.saturation * this.$colorpickerArea.width() / 100;
        this.$colorpickerPointer.css({
            top: (top - 5) + 'px',
            left: (left - 5) + 'px',
        });

        // Update color slider position
        var height = this.$colorSlider.height();
        var y = this.colorComponents.hue * height / 360;
        this.$colorSliderPointer.css('top', Math.round(y - 2));

        if (! this.options.noTransparency) {
            // Update opacity slider position
            var heightOpacity = this.$opacitySlider.height();
            var z = heightOpacity * (1 - this.colorComponents.opacity / 100.0);
            this.$opacitySliderPointer.css('top', Math.round(z - 2));

            // Add gradient color on opacity slider
            this.$opacitySlider.css('background', 'linear-gradient(' + this.colorComponents.hex + ' 0%, transparent 100%)');
        }
    },
    /**
     * Updates colors according to given hex value. Opacity is left unchanged.
     *
     * @private
     * @param {string} hex - hexadecimal code
     */
    _updateHex: function (hex) {
        var rgb = ColorpickerWidget.convertCSSColorToRgba(hex);
        if (!rgb) {
            return;
        }
        _.extend(this.colorComponents,
            {hex: hex},
            rgb,
            ColorpickerWidget.convertRgbToHsl(rgb.red, rgb.green, rgb.blue)
        );
        this._updateCssColor();
    },
    /**
     * Updates colors according to given RGB values.
     *
     * @private
     * @param {integer} r
     * @param {integer} g
     * @param {integer} b
     * @param {integer} [a]
     */
    _updateRgba: function (r, g, b, a) {
        // Remove full transparency in case some lightness is added
        const opacity = a || this.colorComponents.opacity;
        if (opacity < 0.1 && (r > 0.1 || g > 0.1 || b > 0.1)) {
            a = 100;
        }

        // We update the hexadecimal code by transforming into a css color and
        // ignoring the opacity (we don't display opacity component in hexa as
        // not supported on all browsers)
        var hex = ColorpickerWidget.convertRgbaToCSSColor(r, g, b);
        if (!hex) {
            return;
        }
        _.extend(this.colorComponents,
            {red: r, green: g, blue: b},
            a === undefined ? {} : {opacity: a},
            {hex: hex},
            ColorpickerWidget.convertRgbToHsl(r, g, b)
        );
        this._updateCssColor();
    },
    /**
     * Updates colors according to given HSL values.
     *
     * @private
     * @param {integer} h
     * @param {integer} s
     * @param {integer} l
     */
    _updateHsl: function (h, s, l) {
        // Remove full transparency in case some lightness is added
        let a = this.colorComponents.opacity;
        if (a < 0.1 && l > 0.1) {
            a = 100;
        }

        var rgb = ColorpickerWidget.convertHslToRgb(h, s, l);
        if (!rgb) {
            return;
        }
        // We receive an hexa as we ignore the opacity
        const hex = ColorpickerWidget.convertRgbaToCSSColor(rgb.red, rgb.green, rgb.blue);
        _.extend(this.colorComponents,
            {hue: h, saturation: s, lightness: l},
            rgb,
            {hex: hex},
            {opacity: a},
        );
        this._updateCssColor();
    },
    /**
     * Updates color opacity.
     *
     * @private
     * @param {integer} a
     */
    _updateOpacity: function (a) {
        if (a < 0 || a > 100) {
            return;
        }
        _.extend(this.colorComponents,
            {opacity: a}
        );
        this._updateCssColor();
    },
    /**
     * Trigger an event to annonce that the widget value has changed
     *
     * @private
     */
    _colorSelected: function () {
        this.trigger_up('colorpicker_select', this.colorComponents);
    },
    /**
     * Updates css color representation.
     *
     * @private
     */
    _updateCssColor: function () {
        const r = this.colorComponents.red;
        const g = this.colorComponents.green;
        const b = this.colorComponents.blue;
        const a = this.colorComponents.opacity;
        _.extend(this.colorComponents,
            {cssColor: ColorpickerWidget.convertRgbaToCSSColor(r, g, b, a)}
        );
        if (this.previewActive) {
            this.trigger_up('colorpicker_preview', this.colorComponents);
        }
    },

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    /**
     * @private
     * @param {Event} ev
     */
    _onKeypress: function (ev) {
        if (ev.charCode === $.ui.keyCode.ENTER) {
            if (ev.target.tagName === 'INPUT') {
                this._onChangeInputs(ev);
            }
            ev.preventDefault();
            this.trigger_up('enter_key_color_colorpicker');
        }
    },
    /**
     * @param {Event} ev
     */
    _onClick: function (ev) {
        if (this.options.stopClickPropagation) {
            ev.stopPropagation();
        }
        ev.originalEvent.__isColorpickerClick = true;
        $(ev.target).find('> .o_opacity_pointer, > .o_slider_pointer, > .o_picker_pointer').addBack('.o_opacity_pointer, .o_slider_pointer, .o_picker_pointer').focus();
        if (ev.target.dataset.colorMethod === 'hex' && !this.selectedHexValue) {
            ev.target.select();
            this.selectedHexValue = ev.target.value;
            return;
        }
        this.selectedHexValue = '';
    },
    /**
     * Updates color when the user starts clicking on the picker.
     *
     * @private
     * @param {Event} ev
     */
    _onMouseDownPicker: function (ev) {
        this.pickerFlag = true;
        ev.preventDefault();
        this._onMouseMovePicker(ev);
    },
    /**
     * Updates saturation and lightness values on mouse drag over picker.
     *
     * @private
     * @param {Event} ev
     */
    _onMouseMovePicker: function (ev) {
        if (!this.pickerFlag) {
            return;
        }

        var offset = this.$colorpickerArea.offset();
        var top = ev.pageY - offset.top;
        var left = ev.pageX - offset.left;
        var saturation = Math.round(100 * left / this.$colorpickerArea.width());
        var lightness = Math.round(100 * (this.$colorpickerArea.height() - top) / this.$colorpickerArea.height());
        saturation = utils.confine(saturation, 0, 100);
        lightness = utils.confine(lightness, 0, 100);

        this._updateHsl(this.colorComponents.hue, saturation, lightness);
        this._updateUI();
    },
    /**
     * Updates color when user starts clicking on slider.
     *
     * @private
     * @param {Event} ev
     */
    _onMouseDownSlider: function (ev) {
        this.sliderFlag = true;
        ev.preventDefault();
        this._onMouseMoveSlider(ev);
    },
    /**
     * Updates hue value on mouse drag over slider.
     *
     * @private
     * @param {Event} ev
     */
    _onMouseMoveSlider: function (ev) {
        if (!this.sliderFlag) {
            return;
        }

        var y = ev.pageY - this.$colorSlider.offset().top;
        var hue = Math.round(360 * y / this.$colorSlider.height());
        hue = utils.confine(hue, 0, 360);

        this._updateHsl(hue, this.colorComponents.saturation, this.colorComponents.lightness);
        this._updateUI();
    },
    /**
     * Updates opacity when user starts clicking on opacity slider.
     *
     * @private
     * @param {Event} ev
     */
    _onMouseDownOpacitySlider: function (ev) {
        this.opacitySliderFlag = true;
        ev.preventDefault();
        this._onMouseMoveOpacitySlider(ev);
    },
    /**
     * Updates opacity value on mouse drag over opacity slider.
     *
     * @private
     * @param {Event} ev
     */
    _onMouseMoveOpacitySlider: function (ev) {
        if (!this.opacitySliderFlag || this.options.noTransparency) {
            return;
        }

        var y = ev.pageY - this.$opacitySlider.offset().top;
        var opacity = Math.round(100 * (1 - y / this.$opacitySlider.height()));
        opacity = utils.confine(opacity, 0, 100);

        this._updateOpacity(opacity);
        this._updateUI();
    },
    /**
     * Called when input value is changed -> Updates UI: Set picker and slider
     * position and set colors.
     *
     * @private
     * @param {Event} ev
     */
    _onChangeInputs: function (ev) {
        switch ($(ev.target).data('colorMethod')) {
            case 'hex':
                this._updateHex(this.$('.o_hex_input').val());
                break;
            case 'rgb':
                this._updateRgba(
                    parseInt(this.$('.o_red_input').val()),
                    parseInt(this.$('.o_green_input').val()),
                    parseInt(this.$('.o_blue_input').val())
                );
                break;
            case 'hsl':
                this._updateHsl(
                    parseInt(this.$('.o_hue_input').val()),
                    parseInt(this.$('.o_saturation_input').val()),
                    parseInt(this.$('.o_lightness_input').val())
                );
                break;
            case 'opacity':
                this._updateOpacity(parseInt(this.$('.o_opacity_input').val()));
                break;
        }
        this._updateUI();
        this._colorSelected();
    },
});

//--------------------------------------------------------------------------
// Static
//--------------------------------------------------------------------------

/**
 * Converts RGB color components to HSL components.
 *
 * @static
 * @param {integer} r - [0, 255]
 * @param {integer} g - [0, 255]
 * @param {integer} b - [0, 255]
 * @returns {Object|false}
 *          - hue [0, 360[ (float)
 *          - saturation [0, 100] (float)
 *          - lightness [0, 100] (float)
 */
ColorpickerWidget.convertRgbToHsl = function (r, g, b) {
    if (typeof (r) !== 'number' || isNaN(r) || r < 0 || r > 255
            || typeof (g) !== 'number' || isNaN(g) || g < 0 || g > 255
            || typeof (b) !== 'number' || isNaN(b) || b < 0 || b > 255) {
        return false;
    }

    var red = r / 255;
    var green = g / 255;
    var blue = b / 255;
    var maxColor = Math.max(red, green, blue);
    var minColor = Math.min(red, green, blue);
    var delta = maxColor - minColor;
    var hue = 0;
    var saturation = 0;
    var lightness = (maxColor + minColor) / 2;
    if (delta) {
        if (maxColor === red) {
            hue = (green - blue) / delta;
        }
        if (maxColor === green) {
            hue = 2 + (blue - red) / delta;
        }
        if (maxColor === blue) {
            hue = 4 + (red - green) / delta;
        }
        if (maxColor) {
            saturation = delta / (1 - Math.abs(2 * lightness - 1));
        }
    }
    hue = 60 * hue;
    return {
        hue: hue < 0 ? hue + 360 : hue,
        saturation: saturation * 100,
        lightness: lightness * 100,
    };
};
/**
 * Converts HSL color components to RGB components.
 *
 * @static
 * @param {number} h - [0, 360[ (float)
 * @param {number} s - [0, 100] (float)
 * @param {number} l - [0, 100] (float)
 * @returns {Object|false}
 *          - red [0, 255] (integer)
 *          - green [0, 255] (integer)
 *          - blue [0, 255] (integer)
 */
ColorpickerWidget.convertHslToRgb = function (h, s, l) {
    if (typeof (h) !== 'number' || isNaN(h) || h < 0 || h > 360
            || typeof (s) !== 'number' || isNaN(s) || s < 0 || s > 100
            || typeof (l) !== 'number' || isNaN(l) || l < 0 || l > 100) {
        return false;
    }

    var huePrime = h / 60;
    var saturation = s / 100;
    var lightness = l / 100;
    var chroma = saturation * (1 - Math.abs(2 * lightness - 1));
    var secondComponent = chroma * (1 - Math.abs(huePrime % 2 - 1));
    var lightnessAdjustment = lightness - chroma / 2;
    var precision = 255;
    chroma = Math.round((chroma + lightnessAdjustment) * precision);
    secondComponent = Math.round((secondComponent + lightnessAdjustment) * precision);
    lightnessAdjustment = Math.round((lightnessAdjustment) * precision);
    if (huePrime >= 0 && huePrime < 1) {
        return {
            red: chroma,
            green: secondComponent,
            blue: lightnessAdjustment,
        };
    }
    if (huePrime >= 1 && huePrime < 2) {
        return {
            red: secondComponent,
            green: chroma,
            blue: lightnessAdjustment,
        };
    }
    if (huePrime >= 2 && huePrime < 3) {
        return {
            red: lightnessAdjustment,
            green: chroma,
            blue: secondComponent,
        };
    }
    if (huePrime >= 3 && huePrime < 4) {
        return {
            red: lightnessAdjustment,
            green: secondComponent,
            blue: chroma,
        };
    }
    if (huePrime >= 4 && huePrime < 5) {
        return {
            red: secondComponent,
            green: lightnessAdjustment,
            blue: chroma,
        };
    }
    if (huePrime >= 5 && huePrime <= 6) {
        return {
            red: chroma,
            green: lightnessAdjustment,
            blue: secondComponent,
        };
    }
    return false;
};
/**
 * Converts RGBA color components to a normalized CSS color: if the opacity
 * is invalid or equal to 100, a hex is returned; otherwise a rgba() css color
 * is returned.
 *
 * Those choice have multiple reason:
 * - A hex color is more common to c/c from other utilities on the web and is
 *   also shorter than rgb() css colors
 * - Opacity in hexadecimal notations is not supported on all browsers and is
 *   also less common to use.
 *
 * @static
 * @param {integer} r - [0, 255]
 * @param {integer} g - [0, 255]
 * @param {integer} b - [0, 255]
 * @param {float} a - [0, 100]
 * @returns {string}
 */
ColorpickerWidget.convertRgbaToCSSColor = function (r, g, b, a) {
    if (typeof (r) !== 'number' || isNaN(r) || r < 0 || r > 255
            || typeof (g) !== 'number' || isNaN(g) || g < 0 || g > 255
            || typeof (b) !== 'number' || isNaN(b) || b < 0 || b > 255) {
        return false;
    }
    if (typeof (a) !== 'number' || isNaN(a) || a < 0 || Math.abs(a - 100) < Number.EPSILON) {
        const rr = r < 16 ? '0' + r.toString(16) : r.toString(16);
        const gg = g < 16 ? '0' + g.toString(16) : g.toString(16);
        const bb = b < 16 ? '0' + b.toString(16) : b.toString(16);
        return (`#${rr}${gg}${bb}`).toUpperCase();
    }
    return `rgba(${r}, ${g}, ${b}, ${parseFloat((a / 100.0).toFixed(3))})`;
};
/**
 * Converts a CSS color (rgb(), rgba(), hexadecimal) to RGBA color components.
 *
 * Note: we don't support using and displaying hexadecimal color with opacity
 * but this method allows to receive one and returns the correct opacity value.
 *
 * @static
 * @param {string} cssColor - hexadecimal code or rgb() or rgba()
 * @returns {Object|false}
 *          - red [0, 255] (integer)
 *          - green [0, 255] (integer)
 *          - blue [0, 255] (integer)
 *          - opacity [0, 100.0] (float)
 */
ColorpickerWidget.convertCSSColorToRgba = function (cssColor) {
    // Check if cssColor is a rgba() or rgb() color
    const rgba = cssColor.match(/^rgba?\((\d+),\s*(\d+),\s*(\d+)(?:,\s*(\d+(?:\.\d+)?))?\)$/);
    if (rgba) {
        if (rgba[4] === undefined) {
            rgba[4] = 1;
        }
        return {
            red: parseInt(rgba[1]),
            green: parseInt(rgba[2]),
            blue: parseInt(rgba[3]),
            opacity: Math.round(parseFloat(rgba[4]) * 100),
        };
    }

    // Otherwise, check if cssColor is an hexadecimal code color
    if (/^#([0-9A-F]{6}|[0-9A-F]{8})$/i.test(cssColor)) {
        return {
            red: parseInt(cssColor.substr(1, 2), 16),
            green: parseInt(cssColor.substr(3, 2), 16),
            blue: parseInt(cssColor.substr(5, 2), 16),
            opacity: (cssColor.length === 9 ? (parseInt(cssColor.substr(7, 2), 16) / 255) : 1) * 100,
        };
    }

    // TODO maybe implement a support for receiving css color like 'red' or
    // 'transparent' (which are now considered non-css color by isCSSColor...)
    // Note: however, if ever implemented be careful of 'white'/'black' which
    // actually are color names for our color system...

    return false;
};
/**
 * Converts a CSS color (rgb(), rgba(), hexadecimal) to a normalized version
 * of the same color (@see convertRgbaToCSSColor).
 *
 * Normalized color can be safely compared using string comparison.
 *
 * @static
 * @param {string} cssColor - hexadecimal code or rgb() or rgba()
 * @returns {string} - the normalized css color or the given css color if it
 *                     failed to be normalized
 */
ColorpickerWidget.normalizeCSSColor = function (cssColor) {
    const rgba = ColorpickerWidget.convertCSSColorToRgba(cssColor);
    if (!rgba) {
        return cssColor;
    }
    return ColorpickerWidget.convertRgbaToCSSColor(rgba.red, rgba.green, rgba.blue, rgba.opacity);
};
/**
 * Checks if a given string is a css color.
 *
 * @static
 * @param {string} cssColor
 * @returns {boolean}
 */
ColorpickerWidget.isCSSColor = function (cssColor) {
    return ColorpickerWidget.convertCSSColorToRgba(cssColor) !== false;
};

/**
 * Mixes two colors by applying a weighted average of their red, green and blue
 * components.
 *
 * @static
 * @param {string} cssColor1 - hexadecimal code or rgb() or rgba()
 * @param {string} cssColor2 - hexadecimal code or rgb() or rgba()
 * @param {number} weight - a number between 0 and 1
 * @returns {string} - mixed color in hexadecimal format
 */
ColorpickerWidget.mixCssColors = function (cssColor1, cssColor2, weight) {
    const rgba1 = ColorpickerWidget.convertCSSColorToRgba(cssColor1);
    const rgba2 = ColorpickerWidget.convertCSSColorToRgba(cssColor2);
    const rgb1 = [rgba1.red, rgba1.green, rgba1.blue];
    const rgb2 = [rgba2.red, rgba2.green, rgba2.blue];
    const [r, g, b] = rgb1.map((_, idx) => Math.round(rgb2[idx] + (rgb1[idx] - rgb2[idx]) * weight));
    return ColorpickerWidget.convertRgbaToCSSColor(r, g, b);
};

const ColorpickerDialog = Dialog.extend({
    /**
     * @override
     */
    init: function (parent, options) {
        this.options = options || {};
        this._super(parent, _.extend({
            size: 'small',
            title: _t('Pick a color'),
            buttons: [
                {text: _t('Choose'), classes: 'btn-primary', close: true, click: this._onFinalPick.bind(this)},
                {text: _t('Discard'), close: true},
            ],
        }, this.options));
    },
    /**
     * @override
     */
    start: function () {
        const proms = [this._super(...arguments)];
        this.colorPicker = new ColorpickerWidget(this, _.extend({
            colorPreview: true,
        }, this.options));
        proms.push(this.colorPicker.appendTo(this.$el));
        return Promise.all(proms);
    },

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    /**
     * @private
     */
    _onFinalPick: function () {
        this.trigger_up('colorpicker:saved', this.colorPicker.colorComponents);
    },
});

return {
    ColorpickerDialog: ColorpickerDialog,
    ColorpickerWidget: ColorpickerWidget,
};
});
