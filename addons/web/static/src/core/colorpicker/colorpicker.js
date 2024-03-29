/** @odoo-module **/

import {
    convertCSSColorToRgba,
    convertRgbaToCSSColor,
    convertRgbToHsl,
    convertHslToRgb,
} from "@web/core/utils/colors";
import { uniqueId } from "@web/core/utils/functions";
import { clamp } from "@web/core/utils/numbers";
import { throttleForAnimation } from "@web/core/utils/timing";

import {
    Component,
    useRef,
    onWillStart,
    onMounted,
    onWillUpdateProps,
    onWillDestroy,
} from "@odoo/owl";

export class Colorpicker extends Component {
    static template = "web.Colorpicker";
    static props = {
        document: { type: true, optional: true },
        defaultColor: { type: String, optional: true },
        selectedColor: { type: String, optional: true },
        noTransparency: { type: Boolean, optional: true },
        colorPreview: { type: Boolean, optional: true },
        stopClickPropagation: { type: Boolean, optional: true },
        onColorSelect: { type: Function, optional: true },
        onColorPreview: { type: Function, optional: true },
        onInputEnter: { type: Function, optional: true },
    };
    static defaultProps = {
        document: window.document,
        defaultColor: "#FF0000",
        noTransparency: false,
        colorPreview: false,
        stopClickPropagation: false,
        onColorSelect: () => {},
        onColorPreview: () => {},
        onInputEnter: () => {},
    };

    elRef = useRef("el");

    setup() {
        onWillStart(() => {
            this.init();
        });
        onMounted(async () => {
            if (!this.elRef.el) {
                // There is legacy code that can trigger the instantiation of the
                // link tool when one of it's parent component is not in the dom. If
                // that parent element is not in the dom, owl will not return
                // `this.linkComponentWrapperRef.el` because of a check (see
                // `inOwnerDocument`).
                // Todo: this workaround should be removed when the snippet menu is
                // converted to owl.
                await new Promise((resolve) => {
                    const observer = new MutationObserver(() => {
                        if (this.elRef.el) {
                            observer.disconnect();
                            resolve();
                        }
                    });
                    observer.observe(document.body, { childList: true, subtree: true });
                });
            }
            this.el = this.elRef.el;
            this.$el = $(this.el);

            this.$el.on("click", this._onClick.bind(this));
            this.$el.on("keypress", this._onKeypress.bind(this));
            this.$el.on("mousedown", ".o_color_pick_area", this._onMouseDownPicker.bind(this));
            this.$el.on("mousedown", ".o_color_slider", this._onMouseDownSlider.bind(this));
            this.$el.on(
                "mousedown",
                ".o_opacity_slider",
                this._onMouseDownOpacitySlider.bind(this)
            );
            this.$el.on("change", ".o_color_picker_inputs", this._onChangeInputs.bind(this));

            this.start();
        });
        onWillUpdateProps((newProps) => {
            if (newProps.selectedColor) {
                this.setSelectedColor(newProps.selectedColor);
            }
        });
        onWillDestroy(() => {
            this.destroy();
        });
    }

    init() {
        this.pickerFlag = false;
        this.sliderFlag = false;
        this.opacitySliderFlag = false;
        this.colorComponents = {};
        this.uniqueId = uniqueId("colorpicker");
        this.selectedHexValue = "";
    }
    /**
     * @override
     */
    start() {
        this.$colorpickerArea = this.$el.find(".o_color_pick_area");
        this.$colorpickerPointer = this.$el.find(".o_picker_pointer");
        this.$colorSlider = this.$el.find(".o_color_slider");
        this.$colorSliderPointer = this.$el.find(".o_slider_pointer");
        this.$opacitySlider = this.$el.find(".o_opacity_slider");
        this.$opacitySliderPointer = this.$el.find(".o_opacity_pointer");

        const rgba = convertCSSColorToRgba(this.props.defaultColor);
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
        this.$documents = $(
            [
                window.top,
                ...Array.from(window.top.frames).filter((frame) => {
                    try {
                        const document = frame.document;
                        return !!document;
                    } catch {
                        // We cannot access the document (cross origin).
                        return false;
                    }
                }),
            ].map((w) => w.document)
        );
        this.throttleOnMouseMove = throttleForAnimation((ev) => {
            this._onMouseMovePicker(ev);
            this._onMouseMoveSlider(ev);
            this._onMouseMoveOpacitySlider(ev);
        });
        this.$documents.on(`mousemove.${this.uniqueId}`, this.throttleOnMouseMove);
        this.$documents.on(`mouseup.${this.uniqueId}`, () => {
            if (this.pickerFlag || this.sliderFlag || this.opacitySliderFlag) {
                this._colorSelected();
            }
            this.pickerFlag = false;
            this.sliderFlag = false;
            this.opacitySliderFlag = false;
        });

        this.previewActive = true;
    }
    /**
     * @override
     */
    destroy() {
        if (this.throttleOnMouseMove) {
            this.$documents.off(`.${this.uniqueId}`);
            this.throttleOnMouseMove.cancel();
        }
    }
    /**
     * Sets the currently selected color
     *
     * @param {string} color rgb[a]
     */
    setSelectedColor(color) {
        const rgba = convertCSSColorToRgba(color);
        if (rgba) {
            const oldPreviewActive = this.previewActive;
            this.previewActive = false;
            this._updateRgba(rgba.red, rgba.green, rgba.blue, rgba.opacity);
            this.previewActive = oldPreviewActive;
            this._updateUI();
        }
    }

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * Updates input values, color preview, picker and slider pointer positions.
     *
     * @private
     */
    _updateUI() {
        // Update inputs
        for (const [color, value] of Object.entries(this.colorComponents)) {
            this.$el.find(`.o_${color}_input`).val(value);
        }

        // Update preview
        this.$el.find(".o_color_preview").css("background-color", this.colorComponents.cssColor);

        // Update picker area and picker pointer position
        this.$colorpickerArea.css(
            "background-color",
            `hsl(${this.colorComponents.hue}, 100%, 50%)`
        );
        const top = ((100 - this.colorComponents.lightness) * this.$colorpickerArea.height()) / 100;
        const left = (this.colorComponents.saturation * this.$colorpickerArea.width()) / 100;
        this.$colorpickerPointer.css({
            top: top - 5 + "px",
            left: left - 5 + "px",
        });

        // Update color slider position
        const height = this.$colorSlider.height();
        const y = (this.colorComponents.hue * height) / 360;
        this.$colorSliderPointer.css("top", Math.round(y - 2));

        if (!this.props.noTransparency) {
            // Update opacity slider position
            const heightOpacity = this.$opacitySlider.height();
            const z = heightOpacity * (1 - this.colorComponents.opacity / 100.0);
            this.$opacitySliderPointer.css("top", Math.round(z - 2));

            // Add gradient color on opacity slider
            this.$opacitySlider.css(
                "background",
                "linear-gradient(" + this.colorComponents.hex + " 0%, transparent 100%)"
            );
        }
    }
    /**
     * Updates colors according to given hex value. Opacity is left unchanged.
     *
     * @private
     * @param {string} hex - hexadecimal code
     */
    _updateHex(hex) {
        const rgb = convertCSSColorToRgba(hex);
        if (!rgb) {
            return;
        }
        Object.assign(
            this.colorComponents,
            { hex: hex },
            rgb,
            convertRgbToHsl(rgb.red, rgb.green, rgb.blue)
        );
        this._updateCssColor();
    }
    /**
     * Updates colors according to given RGB values.
     *
     * @private
     * @param {integer} r
     * @param {integer} g
     * @param {integer} b
     * @param {integer} [a]
     */
    _updateRgba(r, g, b, a) {
        // Remove full transparency in case some lightness is added
        const opacity = a || this.colorComponents.opacity;
        if (opacity < 0.1 && (r > 0.1 || g > 0.1 || b > 0.1)) {
            a = 100;
        }

        // We update the hexadecimal code by transforming into a css color and
        // ignoring the opacity (we don't display opacity component in hexa as
        // not supported on all browsers)
        const hex = convertRgbaToCSSColor(r, g, b);
        if (!hex) {
            return;
        }
        Object.assign(
            this.colorComponents,
            { red: r, green: g, blue: b },
            a === undefined ? {} : { opacity: a },
            { hex: hex },
            convertRgbToHsl(r, g, b)
        );
        this._updateCssColor();
    }
    /**
     * Updates colors according to given HSL values.
     *
     * @private
     * @param {integer} h
     * @param {integer} s
     * @param {integer} l
     */
    _updateHsl(h, s, l) {
        // Remove full transparency in case some lightness is added
        let a = this.colorComponents.opacity;
        if (a < 0.1 && l > 0.1) {
            a = 100;
        }

        const rgb = convertHslToRgb(h, s, l);
        if (!rgb) {
            return;
        }
        // We receive an hexa as we ignore the opacity
        const hex = convertRgbaToCSSColor(rgb.red, rgb.green, rgb.blue);
        Object.assign(
            this.colorComponents,
            { hue: h, saturation: s, lightness: l },
            rgb,
            { hex: hex },
            { opacity: a }
        );
        this._updateCssColor();
    }
    /**
     * Updates color opacity.
     *
     * @private
     * @param {integer} a
     */
    _updateOpacity(a) {
        if (a < 0 || a > 100) {
            return;
        }
        Object.assign(this.colorComponents, { opacity: a });
        this._updateCssColor();
    }
    /**
     * Trigger an event to annonce that the widget value has changed
     *
     * @private
     */
    _colorSelected() {
        this.props.onColorSelect(this.colorComponents);
    }
    /**
     * Updates css color representation.
     *
     * @private
     */
    _updateCssColor() {
        const r = this.colorComponents.red;
        const g = this.colorComponents.green;
        const b = this.colorComponents.blue;
        const a = this.colorComponents.opacity;
        Object.assign(this.colorComponents, { cssColor: convertRgbaToCSSColor(r, g, b, a) });
        if (this.previewActive) {
            this.props.onColorPreview(this.colorComponents);
        }
    }

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    /**
     * @private
     * @param {Event} ev
     */
    _onKeypress(ev) {
        if (ev.key === "Enter") {
            if (ev.target.tagName === "INPUT") {
                this._onChangeInputs(ev);
            }
            ev.preventDefault();
            this.props.onInputEnter(ev);
        }
    }
    /**
     * @param {Event} ev
     */
    _onClick(ev) {
        if (this.props.stopClickPropagation) {
            ev.stopPropagation();
        }
        ev.originalEvent.__isColorpickerClick = true;
        $(ev.target)
            .find("> .o_opacity_pointer, > .o_slider_pointer, > .o_picker_pointer")
            .addBack(".o_opacity_pointer, .o_slider_pointer, .o_picker_pointer")
            .focus();
        if (ev.target.dataset.colorMethod === "hex" && !this.selectedHexValue) {
            ev.target.select();
            this.selectedHexValue = ev.target.value;
            return;
        }
        this.selectedHexValue = "";
    }
    /**
     * Updates color when the user starts clicking on the picker.
     *
     * @private
     * @param {Event} ev
     */
    _onMouseDownPicker(ev) {
        this.pickerFlag = true;
        ev.preventDefault();
        this._onMouseMovePicker(ev);
    }
    /**
     * Updates saturation and lightness values on mouse drag over picker.
     *
     * @private
     * @param {Event} ev
     */
    _onMouseMovePicker(ev) {
        if (!this.pickerFlag) {
            return;
        }

        const offset = this.$colorpickerArea.offset();
        const top = ev.pageY - offset.top;
        const left = ev.pageX - offset.left;
        let saturation = Math.round((100 * left) / this.$colorpickerArea.width());
        let lightness = Math.round(
            (100 * (this.$colorpickerArea.height() - top)) / this.$colorpickerArea.height()
        );
        saturation = clamp(saturation, 0, 100);
        lightness = clamp(lightness, 0, 100);

        this._updateHsl(this.colorComponents.hue, saturation, lightness);
        this._updateUI();
    }
    /**
     * Updates color when user starts clicking on slider.
     *
     * @private
     * @param {Event} ev
     */
    _onMouseDownSlider(ev) {
        this.sliderFlag = true;
        ev.preventDefault();
        this._onMouseMoveSlider(ev);
    }
    /**
     * Updates hue value on mouse drag over slider.
     *
     * @private
     * @param {Event} ev
     */
    _onMouseMoveSlider(ev) {
        if (!this.sliderFlag) {
            return;
        }

        const y = ev.pageY - this.$colorSlider.offset().top;
        let hue = Math.round((360 * y) / this.$colorSlider.height());
        hue = clamp(hue, 0, 360);

        this._updateHsl(hue, this.colorComponents.saturation, this.colorComponents.lightness);
        this._updateUI();
    }
    /**
     * Updates opacity when user starts clicking on opacity slider.
     *
     * @private
     * @param {Event} ev
     */
    _onMouseDownOpacitySlider(ev) {
        this.opacitySliderFlag = true;
        ev.preventDefault();
        this._onMouseMoveOpacitySlider(ev);
    }
    /**
     * Updates opacity value on mouse drag over opacity slider.
     *
     * @private
     * @param {Event} ev
     */
    _onMouseMoveOpacitySlider(ev) {
        if (!this.opacitySliderFlag || this.props.noTransparency) {
            return;
        }

        const y = ev.pageY - this.$opacitySlider.offset().top;
        let opacity = Math.round(100 * (1 - y / this.$opacitySlider.height()));
        opacity = clamp(opacity, 0, 100);

        this._updateOpacity(opacity);
        this._updateUI();
    }
    /**
     * Called when input value is changed -> Updates UI: Set picker and slider
     * position and set colors.
     *
     * @private
     * @param {Event} ev
     */
    _onChangeInputs(ev) {
        switch ($(ev.target).data("colorMethod")) {
            case "hex":
                this._updateHex(this.$el.find(".o_hex_input").val());
                break;
            case "rgb":
                this._updateRgba(
                    parseInt(this.$el.find(".o_red_input").val()),
                    parseInt(this.$el.find(".o_green_input").val()),
                    parseInt(this.$el.find(".o_blue_input").val())
                );
                break;
            case "hsl":
                this._updateHsl(
                    parseInt(this.$el.find(".o_hue_input").val()),
                    parseInt(this.$el.find(".o_saturation_input").val()),
                    parseInt(this.$el.find(".o_lightness_input").val())
                );
                break;
            case "opacity":
                this._updateOpacity(parseInt(this.$el.find(".o_opacity_input").val()));
                break;
        }
        this._updateUI();
        this._colorSelected();
    }
}
