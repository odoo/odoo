import { getActiveHotkey } from "@web/core/hotkeys/hotkey_service";
import { _t } from "@web/core/l10n/translation";
import {
    convertCSSColorToRgba,
    convertHslToRgb,
    convertRgbaToCSSColor,
    convertRgbToHsl,
    normalizeCSSColor,
} from "@web/core/utils/colors";
import { uniqueId } from "@web/core/utils/functions";
import { clamp } from "@web/core/utils/numbers";
import { debounce, useThrottleForAnimation } from "@web/core/utils/timing";

import { Component, onMounted, onWillUpdateProps, useExternalListener, useRef } from "@odoo/owl";

const ARROW_KEYS = ["arrowup", "arrowdown", "arrowleft", "arrowright"];
const SLIDER_KEYS = [...ARROW_KEYS, "pageup", "pagedown", "home", "end"];

const DEFAULT_COLOR = "#FF0000";

export class CustomColorPicker extends Component {
    static template = "web.CustomColorPicker";
    static props = {
        document: { type: true, optional: true },
        defaultColor: { type: String, optional: true },
        selectedColor: { type: String, optional: true },
        noTransparency: { type: Boolean, optional: true },
        stopClickPropagation: { type: Boolean, optional: true },
        onColorSelect: { type: Function, optional: true },
        onColorPreview: { type: Function, optional: true },
        onInputEnter: { type: Function, optional: true },
        defaultOpacity: { type: Number, optional: true },
        setOnCloseCallback: { type: Function, optional: true },
        setOperationCallbacks: { type: Function, optional: true },
    };
    static defaultProps = {
        document: window.document,
        defaultColor: DEFAULT_COLOR,
        defaultOpacity: 100,
        noTransparency: false,
        stopClickPropagation: false,
        onColorSelect: () => {},
        onColorPreview: () => {},
        onInputEnter: () => {},
    };

    setup() {
        this.pickerFlag = false;
        this.sliderFlag = false;
        this.opacitySliderFlag = false;
        if (this.props.defaultOpacity > 0 && this.props.defaultOpacity <= 1) {
            this.props.defaultOpacity *= 100;
        }
        if (this.props.defaultColor.length <= 7) {
            const opacityHex = Math.round((this.props.defaultOpacity / 100) * 255)
                .toString(16)
                .padStart(2, "0");
            this.props.defaultColor += opacityHex;
        }
        this.colorComponents = {};
        this.uniqueId = uniqueId("colorpicker");
        this.selectedHexValue = "";
        this.shouldSetSelectedColor = false;
        this.lastFocusedSliderEl = undefined;
        if (!this.props.selectedColor) {
            this.props.selectedColor = this.props.defaultColor;
        }
        this.debouncedOnChangeInputs = debounce(this.onChangeInputs.bind(this), 10, true);

        this.elRef = useRef("el");
        this.colorPickerAreaRef = useRef("colorPickerArea");
        this.colorPickerPointerRef = useRef("colorPickerPointer");
        this.colorSliderRef = useRef("colorSlider");
        this.colorSliderPointerRef = useRef("colorSliderPointer");
        this.opacitySliderRef = useRef("opacitySlider");
        this.opacitySliderPointerRef = useRef("opacitySliderPointer");

        // Need to be bound on all documents to work in all possible cases (we
        // have to be able to start dragging/moving from the colorpicker to
        // anywhere on the screen, crossing iframes).
        const documents = [
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
        ].map((w) => w.document);
        this.throttleOnPointerMove = useThrottleForAnimation((ev) => {
            this.onPointerMovePicker(ev);
            this.onPointerMoveSlider(ev);
            this.onPointerMoveOpacitySlider(ev);
        });

        for (const doc of documents) {
            useExternalListener(doc, "pointermove", this.throttleOnPointerMove);
            useExternalListener(doc, "pointerup", this.onPointerUp.bind(this));
            useExternalListener(doc, "keydown", this.onEscapeKeydown.bind(this), { capture: true });
        }
        // Apply the previewed custom color when the popover is closed.
        this.props.setOnCloseCallback?.(() => {
            if (this.shouldSetSelectedColor) {
                this._colorSelected();
            }
        });
        this.props.setOperationCallbacks?.({
            getPreviewColor: () => {
                if (this.shouldSetSelectedColor) {
                    return this.colorComponents.hex;
                }
            },
            onApplyCallback: () => {
                this.shouldSetSelectedColor = false;
            },
            // Reapply the current custom color preview after reverting a preview.
            // Typical usecase: 1) modify the custom color, 2) hover one of the
            // black-white tints, 3) hover out.
            onPreviewRevertCallback: () => {
                if (this.previewActive && this.shouldSetSelectedColor) {
                    this.props.onColorPreview(this.colorComponents);
                }
            },
        });
        onMounted(async () => {
            const rgba =
                convertCSSColorToRgba(this.props.selectedColor) ||
                convertCSSColorToRgba(this.props.defaultColor);
            if (rgba) {
                this._updateRgba(rgba.red, rgba.green, rgba.blue, rgba.opacity);
            }

            this.previewActive = true;
            this._updateUI();
        });
        onWillUpdateProps((newProps) => {
            const newSelectedColor = newProps.selectedColor
                ? newProps.selectedColor
                : newProps.defaultColor;
            if (normalizeCSSColor(newSelectedColor) !== this.colorComponents.cssColor) {
                this.setSelectedColor(newSelectedColor);
            }
        });
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
    /**
     * @param {string[]} allowedKeys
     * @returns {string[]} allowed keys + modifiers
     */
    getAllowedHotkeys(allowedKeys) {
        return allowedKeys.flatMap((key) => [key, `control+${key}`]);
    }
    /**
     * @param {HTMLElement} el
     */
    setLastFocusedSliderEl(el) {
        this.lastFocusedSliderEl = el;
        document.activeElement.blur();
    }

    get el() {
        return this.elRef.el;
    }
    /**
     * @param {string} hotkey
     * @param {number} value
     * @param {Object} [options]
     * @param {number} [options.min=0]
     * @param {number} [options.max=100]
     * @param {number} [options.defaultStep=10] - default step
     * @param {number} [options.modifierStep=1] - step when holding ctrl+key
     * @param {number} [options.leap=20] - step for pageup / pagedown
     * @returns {number} updated and clamped value
     */
    handleRangeKeydownValue(
        hotkey,
        value,
        { min = 0, max = 100, defaultStep = 10, modifierStep = 1, leap = 20 } = {}
    ) {
        let step = defaultStep;
        if (hotkey.startsWith("control+")) {
            step = modifierStep;
        }
        const mainKey = hotkey.replace("control+", "");
        if (mainKey === "pageup" || mainKey === "pagedown") {
            step = leap;
        }
        if (["arrowup", "arrowright", "pageup"].includes(mainKey)) {
            value += step;
        } else if (["arrowdown", "arrowleft", "pagedown"].includes(mainKey)) {
            value -= step;
        } else if (mainKey === "home") {
            value = min;
        } else if (mainKey === "end") {
            value = max;
        }
        return clamp(value, min, max);
    }
    /**
     * Selects and applies a currently previewed color if "Enter" was pressed.
     *
     * @param {String} hotkey
     */
    selectColorOnEnter(hotkey) {
        if (hotkey === "enter" && this.shouldSetSelectedColor) {
            this.pickerFlag = false;
            this.sliderFlag = false;
            this.opacitySliderFlag = false;
            this._colorSelected();
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
            const input = this.el.querySelector(`.o_${color}_input`);
            if (input) {
                input.value = value;
            }
        }

        // Update picker area and picker pointer position
        const colorPickerArea = this.colorPickerAreaRef.el;
        colorPickerArea.style.backgroundColor = `hsl(${this.colorComponents.hue}, 100%, 50%)`;
        const top = ((100 - this.colorComponents.lightness) * colorPickerArea.clientHeight) / 100;
        const left = (this.colorComponents.saturation * colorPickerArea.clientWidth) / 100;

        const colorpickerPointer = this.colorPickerPointerRef.el;
        colorpickerPointer.style.top = top - 5 + "px";
        colorpickerPointer.style.left = left - 5 + "px";
        colorpickerPointer.setAttribute(
            "aria-label",
            _t("Saturation: %(saturationLvl)s %. Brightness: %(brightnessLvl)s %", {
                saturationLvl: this.colorComponents.saturation?.toFixed(2) || "0",
                brightnessLvl: this.colorComponents.lightness?.toFixed(2) || "0",
            })
        );

        // Update color slider position
        const colorSlider = this.colorSliderRef.el;
        const height = colorSlider.clientHeight;
        const y = (this.colorComponents.hue * height) / 360;
        this.colorSliderPointerRef.el.style.bottom = `${Math.round(y - 4)}px`;
        this.colorSliderPointerRef.el.setAttribute(
            "aria-valuenow",
            this.colorComponents.hue.toFixed(2)
        );

        if (!this.props.noTransparency) {
            // Update opacity slider position
            const opacitySlider = this.opacitySliderRef.el;
            const heightOpacity = opacitySlider.clientHeight;
            const z = heightOpacity * (1 - this.colorComponents.opacity / 100.0);
            this.opacitySliderPointerRef.el.style.top = `${Math.round(z - 2)}px`;
            this.opacitySliderPointerRef.el.setAttribute(
                "aria-valuenow",
                this.colorComponents.opacity.toFixed(2)
            );

            // Add gradient color on opacity slider
            const sliderColor = this.colorComponents.hex.slice(0, 7);
            opacitySlider.style.background = `linear-gradient(${sliderColor} 0%, transparent 100%)`;
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
            a = this.props.defaultOpacity;
        }

        const hex = convertRgbaToCSSColor(r, g, b, a);
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
        // Remove full darkness/brightness and non-saturation in case hue is changed
        if (0.1 < Math.abs(h - this.colorComponents.hue)) {
            if (l < 0.1 || 99.9 < l) {
                l = 50;
            }
            if (s < 0.1) {
                s = 100;
            }
        }
        // Remove full transparency in case some lightness is added
        let a = this.colorComponents.opacity;
        if (a < 0.1 && l > 0.1) {
            a = this.props.defaultOpacity;
        }

        const rgb = convertHslToRgb(h, s, l);
        if (!rgb) {
            return;
        }
        // We receive an hexa as we ignore the opacity
        const hex = convertRgbaToCSSColor(rgb.red, rgb.green, rgb.blue, a);
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
        const r = this.colorComponents.red;
        const g = this.colorComponents.green;
        const b = this.colorComponents.blue;
        Object.assign(this.colorComponents, { hex: convertRgbaToCSSColor(r, g, b, a) });
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
    onKeydown(ev) {
        if (ev.key === "Enter") {
            if (ev.target.tagName === "INPUT") {
                this.onChangeInputs(ev);
            }
            ev.preventDefault();
            this.props.onInputEnter(ev);
        }
    }
    /**
     * @param {Event} ev
     */
    onClick(ev) {
        if (this.props.stopClickPropagation) {
            ev.stopPropagation();
        }
        //TODO: we should remove it with legacy web_editor
        ev.__isColorpickerClick = true;

        if (ev.target.dataset.colorMethod === "hex" && !this.selectedHexValue) {
            ev.target.select();
            this.selectedHexValue = ev.target.value;
            return;
        }
        this.selectedHexValue = "";
    }
    onPointerUp() {
        if (this.pickerFlag || this.sliderFlag || this.opacitySliderFlag) {
            this.shouldSetSelectedColor = true;
            this._updateCssColor();
        }
        this.pickerFlag = false;
        this.sliderFlag = false;
        this.opacitySliderFlag = false;

        if (this.lastFocusedSliderEl) {
            this.lastFocusedSliderEl.focus();
            this.lastFocusedSliderEl = undefined;
        }
    }
    /**
     * Removes the close callback on Escape, so that a preview is cancelled with
     * escape instead of being applied.
     *
     * @param {KeydownEvent} ev
     */
    onEscapeKeydown(ev) {
        const hotkey = getActiveHotkey(ev);
        if (hotkey === "escape") {
            this.props.setOnCloseCallback?.(() => {});
        }
    }
    /**
     * Updates color when the user starts clicking on the picker.
     *
     * @private
     * @param {Event} ev
     */
    onPointerDownPicker(ev) {
        this.pickerFlag = true;
        ev.preventDefault();
        this.onPointerMovePicker(ev);
        this.setLastFocusedSliderEl(this.colorPickerPointerRef.el);
    }
    /**
     * Updates saturation and lightness values on pointer drag over picker.
     *
     * @private
     * @param {Event} ev
     */
    onPointerMovePicker(ev) {
        if (!this.pickerFlag) {
            return;
        }

        const colorPickerArea = this.colorPickerAreaRef.el;
        const rect = colorPickerArea.getClientRects()[0];
        const top = ev.pageY - rect.top;
        const left = ev.pageX - rect.left;
        let saturation = Math.round((100 * left) / colorPickerArea.clientWidth);
        let lightness = Math.round(
            (100 * (colorPickerArea.clientHeight - top)) / colorPickerArea.clientHeight
        );
        saturation = clamp(saturation, 0, 100);
        lightness = clamp(lightness, 0, 100);

        this._updateHsl(this.colorComponents.hue, saturation, lightness);
        this._updateUI();
    }
    /**
     * Updates saturation and lightness values on arrow keydown over picker.
     *
     * @private
     * @param {Event} ev
     */
    onPickerKeydown(ev) {
        const hotkey = getActiveHotkey(ev);
        this.selectColorOnEnter(hotkey);
        if (!this.getAllowedHotkeys(ARROW_KEYS).includes(hotkey)) {
            return;
        }
        let saturation = this.colorComponents.saturation;
        let lightness = this.colorComponents.lightness;
        let step = 10;
        if (hotkey.startsWith("control+")) {
            step = 1;
        }
        const mainKey = hotkey.replace("control+", "");
        if (mainKey === "arrowup") {
            lightness += step;
        } else if (mainKey === "arrowdown") {
            lightness -= step;
        } else if (mainKey === "arrowright") {
            saturation += step;
        } else if (mainKey === "arrowleft") {
            saturation -= step;
        }
        lightness = clamp(lightness, 0, 100);
        saturation = clamp(saturation, 0, 100);

        this._updateHsl(this.colorComponents.hue, saturation, lightness);
        this._updateUI();
        this.shouldSetSelectedColor = true;
    }
    /**
     * Updates color when user starts clicking on slider.
     *
     * @private
     * @param {Event} ev
     */
    onPointerDownSlider(ev) {
        this.sliderFlag = true;
        ev.preventDefault();
        this.onPointerMoveSlider(ev);
        this.setLastFocusedSliderEl(this.colorSliderPointerRef.el);
    }
    /**
     * Updates hue value on pointer drag over slider.
     *
     * @private
     * @param {Event} ev
     */
    onPointerMoveSlider(ev) {
        if (!this.sliderFlag) {
            return;
        }

        const colorSlider = this.colorSliderRef.el;
        const colorSliderRects = colorSlider.getClientRects();
        const y = colorSliderRects[0].height - (ev.pageY - colorSliderRects[0].top);
        let hue = Math.round((360 * y) / colorSlider.clientHeight);
        hue = clamp(hue, 0, 360);

        this._updateHsl(hue, this.colorComponents.saturation, this.colorComponents.lightness);
        this._updateUI();
    }
    /**
     * Updates hue value on arrow keydown on slider.
     *
     * @param {Event} ev
     */
    onSliderKeydown(ev) {
        const hotkey = getActiveHotkey(ev);
        this.selectColorOnEnter(hotkey);
        if (!this.getAllowedHotkeys(SLIDER_KEYS).includes(hotkey)) {
            return;
        }
        const hue = this.handleRangeKeydownValue(hotkey, this.colorComponents.hue, {
            min: 0,
            max: 360,
            leap: 30,
        });
        this._updateHsl(hue, this.colorComponents.saturation, this.colorComponents.lightness);
        this._updateUI();
        this.shouldSetSelectedColor = true;
    }
    /**
     * Updates opacity when user starts clicking on opacity slider.
     *
     * @private
     * @param {Event} ev
     */
    onPointerDownOpacitySlider(ev) {
        this.opacitySliderFlag = true;
        ev.preventDefault();
        this.onPointerMoveOpacitySlider(ev);
        this.setLastFocusedSliderEl(this.opacitySliderPointerRef.el);
    }
    /**
     * Updates opacity value on pointer drag over opacity slider.
     *
     * @private
     * @param {Event} ev
     */
    onPointerMoveOpacitySlider(ev) {
        if (!this.opacitySliderFlag || this.props.noTransparency) {
            return;
        }

        const opacitySlider = this.opacitySliderRef.el;
        const y = ev.pageY - opacitySlider.getClientRects()[0].top;
        let opacity = Math.round(100 * (1 - y / opacitySlider.clientHeight));
        opacity = clamp(opacity, 0, 100);

        this._updateOpacity(opacity);
        this._updateUI();
    }
    /**
     * Updates opacity value on arrow keydown on opacity slider.
     *
     * @param {Event} ev
     */
    onOpacitySliderKeydown(ev) {
        const hotkey = getActiveHotkey(ev);
        this.selectColorOnEnter(hotkey);
        if (!this.getAllowedHotkeys(SLIDER_KEYS).includes(hotkey)) {
            return;
        }
        const opacity = this.handleRangeKeydownValue(hotkey, this.colorComponents.opacity);

        this._updateOpacity(opacity);
        this._updateUI();
        this.shouldSetSelectedColor = true;
    }
    /**
     * Called when input value is changed -> Updates UI: Set picker and slider
     * position and set colors.
     *
     * @private
     * @param {Event} ev
     */
    onChangeInputs(ev) {
        switch (ev.target.dataset.colorMethod) {
            case "hex":
                // Handled by the "input" event (see "onHexColorInput").
                return;
            case "hsl":
                this._updateHsl(
                    parseInt(this.el.querySelector(".o_hue_input").value),
                    parseInt(this.el.querySelector(".o_saturation_input").value),
                    parseInt(this.el.querySelector(".o_lightness_input").value)
                );
                break;
        }
        this._updateUI();
        this._colorSelected();
    }
    /**
     * Called when the hex color input's input event is triggered.
     *
     * @private
     * @param {Event} ev
     */
    onHexColorInput(ev) {
        const hexColorValue = ev.target.value.replaceAll("#", "");
        if (hexColorValue.length === 6 || hexColorValue.length === 8) {
            this._updateHex(`#${hexColorValue}`);
            this._updateUI();
            this._colorSelected();
        }
    }
}
