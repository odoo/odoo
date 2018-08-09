odoo.define('web_editor.colorpicker', function (require) {
'use strict';

var Widget = require('web.Widget');

return Widget.extend({
    template: 'web_editor.colorpicker',
    xmlDependencies: ['/web_editor/static/src/xml/colorpicker.xml'],
    events: {
        // Picker Events
        'mousedown .o_color_pick_area': '_onMouseDownPicker',
        'mousemove .o_color_pick_area' : '_onMouseMovePicker',
        'mouseup .o_color_pick_area': '_onMouseUpPicker',
        // Slider Events
        'mousedown .o_color_slider': '_onMouseDownSlider',
        'mousemove .o_color_slider' : '_onMouseMoveSlider',
        'mouseup .o_color_slider': '_onMouseUpSlider',
        // Inputs Events
        'change .o_color_picker_inputs' : '_onChangeInputs',
    },
    /**
     * @param {Widget} parent
     * @param {Object} [options]
     * @param {string} [options.defaultHex]
     * @param {string} [options.defaultRGB]
     */
    init: function (parent, options) {
        this._super.apply(this, arguments);
        options = options || {};
        this.pickerFlag = false;
        this.sliderFlag = false;
        this.colors = {};
        if (options.defaultHex) {
            this._updateHex(options.defaultHex);
        } else if (options.defaultRGB) {
            var rgb = options.defaultRGB.match(/rgb\((\d{1,3}), ?(\d{1,3}), ?(\d{1,3})\)/);
            this._updateRgb(parseInt(rgb[1]), parseInt(rgb[2]), parseInt(rgb[3]));
        } else {
            this._updateHex('#FF0000');
        }
    },
    /**
     * @override
     */
    start: function () {
        this._updateUI();
        return this._super.apply(this, arguments);
    },

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * Responsible to update input values, color preview, picker and
     * slider pointer position.
     *
     * @private
     */
    _updateUI: function () {
        var self = this;
        // Update inputs
        _.each(this.colors, function (value, color) {
            self.$(_.str.sprintf('.o-%s-input', color)).val(value);
        });
        // Update preview
        this.$('.o-color-preview').css('background-color', _.str.sprintf('#%s', this.colors.hex));
        // Update picker area and picker pointer position
        this.$('.o_color_pick_area').css('background-color', 'hsl('+ this.colors.hue +', 100%, 50%)');
        var top = (100 - this.colors.lightness) * this.$('.o_color_pick_area').height() / 100;
        var left = (this.$('.o_color_pick_area').width() * this.colors.saturation) / 100;
        this.$('.o_picker_poiner').css({'top': top - 5 + 'px', 'left': left - 5 + 'px'}); // Make cursor in center
        // Update slider position
        var height = this.$('.o_color_slider').height();
        var y = (this.colors.hue * height) / 360;
        this.$('.o_slider_pointer').css('top', Math.round(y - 2));
    },
    /**
     * Update colors when Hex code change.
     *
     * @private
     * @param {string} hex Hexadecimal code
     */
    _updateHex: function (hex) {
        var rgb = this.convertHexToRgb(hex);
        if (rgb) {
            _.extend(this.colors,
                {hex: hex},
                rgb,
                this.convertRgbToHsl(rgb.red, rgb.green, rgb.blue)
            );
        }
    },
    /**
     * Update colors when RGB color value change.
     *
     * @private
     * @param {integer} r red
     * @param {integer} g green
     * @param {integer} b blue
     */
    _updateRgb: function (r, g, b) {
        var hex = this.convertRgbToHex(r, g, b);
        if (hex) {
            _.extend(this.colors,
                {red: r, green: g, blue: b},
                hex,
                this.convertRgbToHsl(r, g, b)
            );
        }
    },
    /**
     * Update colors when HSL color value change.
     *
     * @private
     * @param {integer} h hue
     * @param {integer} s saturation
     * @param {integer} l lightness
     */
    _updateHsl: function (h, s, l) {
        var rgb = this.convertHslToRgb(h, s, l);
        if (rgb) {
            _.extend(this.colors,
                {hue: h, saturation: s, lightness: l},
                rgb,
                this.convertRgbToHex(rgb.red, rgb.green, rgb.blue)
            );
        }
    },

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    /**
     * Update color when user click on picker.
     *
     * @private
     * @param {Event} ev
     */
    _onMouseDownPicker: function (ev) {
        ev.preventDefault();
        this.pickerFlag = true;
        this._onMouseMovePicker(ev);
    },
    /**
     * Update saturation and lightness value when mouse drag over picker.
     *
     * @private
     * @param {Event} ev
     */
    _onMouseMovePicker: function (ev) {
        if (!this.pickerFlag) {
            return;
        }
        var $picker = this.$('.o_color_pick_area');
        var top = Math.round(ev.pageY - $picker.offset().top);
        var left = Math.round(ev.pageX - $picker.offset().left);
        var saturation = Math.round((left * 100) / $picker.width());
        var lightness = Math.round(($picker.height() - top) * 100/$picker.height());
        // Handle when pointer out of box
        saturation = saturation < 0 ? 0 : saturation;
        lightness = lightness < 0 ? 0 : lightness;
        saturation = saturation > 100 ? 100 : saturation;
        lightness = lightness > 100 ? 100 : lightness;
        this._updateHsl(this.colors.hue, saturation, lightness);
        this._updateUI();
    },
    /**
     * @private
     * @param {Event} ev
     */
    _onMouseUpPicker: function (ev) {
        ev.preventDefault();
        this.pickerFlag = false;
    },
    /**
     * Update color when user click on slider.
     *
     * @private
     * @param {Event} ev
     */
    _onMouseDownSlider: function (ev) {
        ev.preventDefault();
        this.sliderFlag = true;
        this._onMouseMoveSlider(ev);
    },
    /**
     * Update hue value when mouse drag over slider.
     *
     * @private
     * @param {Event} ev
     */
    _onMouseMoveSlider: function (ev) {
        if (!this.sliderFlag) {
            return;
        }
        var y = ev.pageY - this.$('.o_color_slider').offset().top;
        var height = this.$('.o_color_slider').height();
        if (y < 0) {
            y = 0;
        }
        if (y > height) {
            y = height;
        }
        var hue = ((360 * y) / height) | 0;
        this._updateHsl(hue, this.colors.saturation, this.colors.lightness);
        this._updateUI();
    },
    /**
     * @private
     * @param {Event} ev
     */
    _onMouseUpSlider: function (ev) {
        this.sliderFlag = false;
    },
    /**
     * Called when input value is changed -> Update UI: Set picker and slider
     * position, Set colors.
     *
     * @private
     * @param {Event} ev
     */
    _onChangeInputs: function (ev) {
        switch ($(ev.target).data('color-method')) {
            case 'hex':
                this._updateHex(this.$('.o-hex-input').val());
                break;
            case 'rgb':
                this._updateRgb(
                    parseInt(this.$('.o-red-input').val()),
                    parseInt(this.$('.o-green-input').val()),
                    parseInt(this.$('.o-blue-input').val())
                );
                break;
            case 'hsl':
                this._updateHsl(
                    parseInt(this.$('.o-hue-input').val()),
                    parseInt(this.$('.o-saturation-input').val()),
                    parseInt(this.$('.o-lightness-input').val())
                );
                break;
        }
        this._updateUI();
    },

    //--------------------------------------------------------------------------
    // Static
    //--------------------------------------------------------------------------

    /**
     * Convert Hexadecimal code to RGB.
     *
     * @static
     * @param {string} hex Hexadecimal code
     * @returns {Object|false} contains red, green and blue.
     */
    convertHexToRgb: function (hex) {
        if (!/(^#[0-9A-F]{6}$)|(^#{0,1}[0-9A-F]{3}$)/i.test(hex)) {
            return false;
        }
        hex = hex.substring(1, hex.length);
        if (hex.length === 3) {
            hex = hex.replace(/([0-9A-F])([0-9A-F])([0-9A-F])/i, '$1$1$2$2$3$3');
        }
        return {
            red: parseInt(hex.substr(0, 2), 16),
            green: parseInt(hex.substr(2, 2), 16),
            blue: parseInt(hex.substr(4, 2), 16),
        };
    },
    /**
     * Convert RGB color to HSL.
     *
     * @static
     * @param {integer} r red
     * @param {integer} g green
     * @param {integer} b blue
     * @returns {Object|false} contains hue, saturation and lightness.
     */
    convertRgbToHsl: function (r, g, b) {
        if (typeof(r) !== 'number' || isNaN(r) || r < 0 || r > 255 ||
            typeof(g) !== 'number' || isNaN(g) || g < 0 || g > 255 ||
            typeof(b) !== 'number' || isNaN(b) || b < 0 || b > 255) {
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
        var X = 1 - Math.abs(2 * lightness - 1);
         if (delta) {
            if (maxColor === red ) {
                hue = (green - blue) / delta;
            }
            if (maxColor === green ) {
                hue = 2 + (blue - red) / delta;
            }
            if (maxColor === blue ) {
                hue = 4 + (red - green) / delta;
            }
            if (maxColor) {
                saturation = delta / X;
            }
        }
        hue = 60 * hue | 0;
        return {
            hue: hue < 0 ? hue += 360 : hue,
            saturation: (saturation * 100) | 0,
            lightness: (lightness * 100) | 0,
        };
    },
    /**
     * Convert HSL color to RGB.
     *
     * @static
     * @param {integer} h hue
     * @param {integer} s saturation
     * @param {integer} l lightness
     * @returns {Object|false} contains red, green and blue.
     */
    convertHslToRgb: function (h, s, l) {
        if (typeof(h) !== 'number' || isNaN(h) || h < 0 || h > 360 ||
            typeof(s) !== 'number' || isNaN(s) || s < 0 || s > 100 ||
            typeof(l) !== 'number' || isNaN(l) || l < 0 || l > 100) {
            return false;
        }
        var huePrime = h / 60;
        var saturation = s / 100;
        var lightness = l / 100;
        var chroma = saturation * (1 - Math.abs(2 * lightness - 1));
        var secondComponent = chroma * (1 - Math.abs(huePrime % 2 - 1));
        var lightnessAdjustment = lightness - chroma/2;
        var precision = 255;
        chroma = (chroma + lightnessAdjustment) * precision | 0;
        secondComponent = (secondComponent + lightnessAdjustment) * precision | 0;
        lightnessAdjustment = lightnessAdjustment * precision | 0;
        if (huePrime >= 0 && huePrime < 1) {
            return {red: chroma, green: secondComponent, blue: lightnessAdjustment};
        }
        if (huePrime >= 1 && huePrime < 2) {
            return {red: secondComponent, green: chroma, blue: lightnessAdjustment};
        }
        if (huePrime >= 2 && huePrime < 3) {
            return {red: lightnessAdjustment, green: chroma, blue: secondComponent};
        }
        if (huePrime >= 3 && huePrime < 4) {
            return {red: lightnessAdjustment, green: secondComponent, blue: chroma};
        }
        if (huePrime >= 4 && huePrime < 5) {
            return {red: secondComponent, green: lightnessAdjustment, blue: chroma};
        }
        if (huePrime >= 5 && huePrime <= 6) {
            return {red: chroma, green: lightnessAdjustment, blue: secondComponent};
        }
    },
    /**
     * Convert RGB color to Hexadecimal code.
     *
     * @static
     * @param {integer} r red
     * @param {integer} g green
     * @param {integer} b blue
     * @returns {Object|false} contain Hexadecimal code.
     */
    convertRgbToHex: function (r, g, b) {
        if (typeof(r) !== 'number' || isNaN(r) || r < 0 || r > 255 ||
            typeof(g) !== 'number' || isNaN(g) || g < 0 || g > 255 ||
            typeof(b) !== 'number' || isNaN(b) || b < 0 || b > 255) {
            return false;
        }
        var red = r < 16 ? '0' + r.toString(16) : r.toString(16);
        var green = g < 16 ? '0' + g.toString(16) : g.toString(16);
        var blue = b < 16 ? '0' + b.toString(16) : b.toString(16);
        return {hex: _.str.sprintf('#%s%s%s', red, green, blue)};
    },
});

});
