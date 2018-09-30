odoo.define('web.colorpicker', function (require) {
'use strict';

var core = require('web.core');
var utils = require('web.utils');
var Dialog = require('web.Dialog');

var _t = core._t;

var Colorpicker = Dialog.extend({
    xmlDependencies: (Dialog.prototype.xmlDependencies || [])
        .concat(['/web/static/src/xml/colorpicker.xml']),

    template: 'web.colorpicker',
    events: _.extend({}, Dialog.prototype.events || {}, {
        'mousedown .o_color_pick_area': '_onMouseDownPicker',
        'mousedown .o_color_slider': '_onMouseDownSlider',
        'mousedown .o_opacity_slider': '_onMouseDownOpacitySlider',
        'change .o_color_picker_inputs' : '_onChangeInputs',
    }),

    /**
     * @constructor
     * @param {Widget} parent
     * @param {Object} [options]
     * @param {string} [options.defaultColor='#FF0000']
     */
    init: function (parent, options) {
        options = options || {};

        this._super(parent, _.extend({
            size: 'medium',
            title: _t('Pick a color'),
            buttons: [
                {text: _t('Choose'), classes: 'btn-primary', close: true, click: this._onFinalPick.bind(this)},
                {text: _t('Discard'), close: true},
            ],
        }, options));
        
        this.pickerFlag = false;
        this.sliderFlag = false;
        this.sliderOpacityFlag = false;
        this.colorComponents = {};

        var self = this;
        var $body = $(document.body);
        $body.on('mousemove.colorpicker', _.throttle(function (ev) {
            self._onMouseMovePicker(ev);
            self._onMouseMoveSlider(ev);
            self._onMouseMoveOpacitySlider(ev);
        }, 10));
        $body.on('mouseup.colorpicker', _.throttle(function (ev) {
            self.pickerFlag = false;
            self.sliderFlag = false;
            self.sliderOpacityFlag = false;
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
        this.$colorOpacity = this.$('.o_opacity_slider');
        this.$colorOpacityPointer = this.$('.o_opacity_pointer');

        var defaultColor = this.options.defaultColor || '#FF0000';
        var rgba = defaultColor.match(/^rgba?\((\d+),\s*(\d+),\s*(\d+)(?:,\s*(\d+(?:\.\d+)?))?\)$/);
        if (rgba) {
            if (rgba[4] == undefined) {
                rgba[4] = 1;
            }
            this._updateRgba(parseInt(rgba[1]), parseInt(rgba[2]), parseInt(rgba[3]), parseFloat(rgba[4]));
        } else {
            this._updateHex(defaultColor);
        }
        this.opened().then(this._updateUI.bind(this));

        return this._super.apply(this, arguments);
    },
    /**
     * @override
     */
    destroy: function () {
        this._super.apply(this, arguments);
        $(document.body).off('.colorpicker');
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
        this.$('.o_color_preview').css('background-color', _.str.sprintf('#%s', this.colorComponents.hex)); // FIXME

        // Update picker area and picker pointer position
        this.$colorpickerArea.css('background-color', _.str.sprintf('hsl(%s, 100%%, 50%%)', this.colorComponents.hue));
        var top = (100 - this.colorComponents.lightness) * this.$colorpickerArea.height() / 100;
        var left = this.colorComponents.saturation * this.$colorpickerArea.width() / 100;
        this.$colorpickerPointer.css({
            top: (top - 5) + 'px',
            left: (left - 5) + 'px',
        });

        // Update slider position
        var height = this.$colorSlider.height();
        var y = this.colorComponents.hue * height / 360;
        this.$colorSliderPointer.css('top', Math.round(y - 2));

        // Update opacity slider position
        var heightOpacity = this.$colorOpacity.height();
        var z = heightOpacity * this.colorComponents.opacity;
        this.$colorOpacityPointer.css('bottom', Math.round(z - 6));

        // Add gradient color on opacity slider
        this.$('.o_opacity_transparent').css('background', 'linear-gradient('+this.colorComponents.hex+' 0%, transparent 100%)');

        // Override update opacity input + update color preview
        this.$('.o_opacity_input').val(Math.floor(z/(heightOpacity/100)));
        this.$('.o_color_preview').css('opacity', this.colorComponents.opacity);
    },
    /**
     * Updates colors according to given hex value.
     *
     * @private
     * @param {string} hex - hexadecimal code
     */
    _updateHex: function (hex) {
        var rgb = Colorpicker.prototype.convertHexToRgb(hex);
        if (!rgb) {
            return;
        }
        _.extend(this.colorComponents,
            {hex: hex},
            rgb,
            Colorpicker.prototype.convertRgbToHsl(rgb.red, rgb.green, rgb.blue)
        );
    },
    /**
     * Updates colors according to given RGB values.
     *
     * @private
     * @param {integer} r
     * @param {integer} g
     * @param {integer} b
     * @param {integer} o
     */
    _updateRgba: function (r, g, b, o) {
        if (o == undefined) {
            o = this.colorComponents.opacity;
        }
        var hex = Colorpicker.prototype.convertRgbToHex(r, g, b);
        if (hex) {
            _.extend(this.colorComponents,
                {red: r, green: g, blue: b},
                {opacity: o},
                hex,
                Colorpicker.prototype.convertRgbToHsl(r, g, b)
            );
        }
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
        var rgb = Colorpicker.prototype.convertHslToRgb(h, s, l);
        if (rgb) {
            _.extend(this.colorComponents,
                {hue: h, saturation: s, lightness: l},
                rgb,
                Colorpicker.prototype.convertRgbToHex(rgb.red, rgb.green, rgb.blue)
            );
        }
    },
    /**
     * Updates color opacity
     *
     * @private
     * @param {integer} o
     */
    _updateOpacity: function (o) {
        _.extend(this.colorComponents,
            {opacity: o}
        );
    },
    /**
     * Updates color opacity
     *
     * @private
     * @param {integer} o
     */
    _updateCssColor: function (r, g, b, o) {
        var cssColor;
        if (this.colorComponents.opacity == 1) {
            cssColor = this.colorComponents.hex;
        } else {
            cssColor = 'rgba('+r+' , '+g+' , '+b+' , '+o+')';
        }
        _.extend(this.colorComponents,
            {cssColor: cssColor}
        );
    },

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    /**
     * Updates color when the user starts clicking on the picker.
     *
     * @private
     * @param {Event} ev
     */
    _onMouseDownPicker: function (ev) {
        this.pickerFlag = true;
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
        this.sliderOpacityFlag = true;
        this._onMouseMoveOpacitySlider(ev);
    },
    /**
     * Updates opacity value on mouse drag over opacity slider.
     *
     * @private
     * @param {Event} ev
     */
    _onMouseMoveOpacitySlider: function (ev) {
        if (!this.sliderOpacityFlag) {
            return;
        }

        var z = ev.pageY - this.$colorOpacity.offset().top;
        
        if (z >= 0 && z <= this.$colorOpacity.height()){
            var z = (1 - z/this.$colorOpacity.height());
            this._updateOpacity(z);
            this._updateUI();
        }
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
                parseInt(this.$('.o_opacity_input').val() * 100);
                break;
        }
        this._updateUI();
    },
    /**
     * @private
     */
    _onFinalPick: function () {
        this._updateCssColor(this.colorComponents.red, this.colorComponents.green, this.colorComponents.blue, this.colorComponents.opacity);
        this.trigger_up('colorpicker:saved', this.colorComponents);
    },

    //--------------------------------------------------------------------------
    // Static
    //--------------------------------------------------------------------------

    /**
     * Converts Hexadecimal code to RGB.
     *
     * @static
     * @param {string} hex - hexadecimal code
     * @returns {Object|false} contains red, green and blue
     */
    convertHexToRgb: function (hex) {
        if (!/^#[0-9A-F]{6}$/i.test(hex)) {
            return false;
        }

        return {
            red: parseInt(hex.substr(1, 2), 16),
            green: parseInt(hex.substr(3, 2), 16),
            blue: parseInt(hex.substr(5, 2), 16),
        };
    },
    /**
     * Converts RGB color to HSL.
     *
     * @static
     * @param {integer} r
     * @param {integer} g
     * @param {integer} b
     * @returns {Object|false} contains hue, saturation and lightness
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
        hue = 60 * hue | 0;
        return {
            hue: hue < 0 ? hue += 360 : hue,
            saturation: (saturation * 100) | 0,
            lightness: (lightness * 100) | 0,
        };
    },
    /**
     * Converts HSL color to RGB.
     *
     * @static
     * @param {integer} h
     * @param {integer} s
     * @param {integer} l
     * @returns {Object|false} contains red, green and blue
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
     * Converts RGB color to Hexadecimal code.
     *
     * @static
     * @param {integer} r
     * @param {integer} g
     * @param {integer} b
     * @returns {Object|false} contains hexadecimal code
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

return Colorpicker;
});
