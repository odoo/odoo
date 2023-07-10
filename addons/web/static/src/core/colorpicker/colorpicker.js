/** @odoo-module **/

import core from "web.core";
import utils from "web.utils";
import Widget from "web.Widget";
import { uniqueId } from "@web/core/utils/functions";
import { debounce, throttleForAnimation } from "@web/core/utils/timing";

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
        this.uniqueId = uniqueId("colorpicker");
        this.selectedHexValue = '';

        this.options = Object.assign({}, options);
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

        // Need to be bound on all documents to work in all possible cases (we
        // have to be able to start dragging/moving from the colorpicker to
        // anywhere on the screen, crossing iframes).
        this.$documents = $([window.top, ...Array.from(window.top.frames).filter(frame => {
            try {
                const document = frame.document;
                return !!document;
            } catch {
                // We cannot access the document (cross origin).
                return false;
            }
        })].map(w => w.document));
        this.throttleOnMouseMove = throttleForAnimation((ev) => {
            this._onMouseMovePicker(ev);
            this._onMouseMoveSlider(ev);
            this._onMouseMoveOpacitySlider(ev);
        });
        this.$documents.on(`mousemove.${this.uniqueId}`, this.throttleOnMouseMove);
        this.$documents.on(`mouseup.${this.uniqueId}`, debounce((ev) => {
            if (this.pickerFlag || this.sliderFlag || this.opacitySliderFlag) {
                this._colorSelected();
            }
            this.pickerFlag = false;
            this.sliderFlag = false;
            this.opacitySliderFlag = false;
        }, 10));

        this.previewActive = true;
        return this._super.apply(this, arguments);
    },
    /**
     * @override
     */
    destroy: function () {
        this._super.apply(this, arguments);
        if (this.throttleOnMouseMove) {
            this.$documents.off(`.${this.uniqueId}`);
            this.throttleOnMouseMove.cancel();
        }
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
        for (const [color, value] of Object.entries(this.colorComponents)) {
            self.$(`.o_${color}_input`).val(value);
        }

        // Update preview
        this.$('.o_color_preview').css('background-color', this.colorComponents.cssColor);

        // Update picker area and picker pointer position
        this.$colorpickerArea.css(
            "background-color",
            `hsl(${this.colorComponents.hue}, 100%, 50%)`
        );
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
        Object.assign(this.colorComponents,
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
        Object.assign(this.colorComponents,
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
        Object.assign(this.colorComponents,
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
        Object.assign(this.colorComponents,
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
        Object.assign(this.colorComponents,
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
