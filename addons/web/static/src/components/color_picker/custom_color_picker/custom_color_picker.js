// @ts-check
/** @odoo-module native */

import {
    Component,
    onMounted,
    onWillUnmount,
    onWillUpdateProps,
    useExternalListener,
    useRef,
} from "@odoo/owl";
import { getActiveHotkey } from "@web/core/browser/hotkeys";
import { makeLogger } from "@web/core/debug/debug_logger";
import { _t } from "@web/core/translation";
import {
    convertCSSColorToRgba,
    convertHslToRgb,
    convertRgbaToCSSColor,
    convertRgbToHsl,
    normalizeCSSColor,
    opacityToHex,
} from "@web/core/utils/format/colors";
import { clamp } from "@web/core/utils/format/numbers";
import { uniqueId } from "@web/core/utils/functions";
import { useThrottleForAnimation } from "@web/core/utils/timing";

const log = makeLogger("web.components.custom_color_picker");

const ARROW_KEYS = ["arrowup", "arrowdown", "arrowleft", "arrowright"];
const SLIDER_KEYS = [...ARROW_KEYS, "pageup", "pagedown", "home", "end"];

const DEFAULT_COLOR = "#FF0000";
const DEFAULT_RGBA = { red: 0xff, green: 0x00, blue: 0x00, opacity: 100 };

export class CustomColorPicker extends Component {
    static template = "web.CustomColorPicker";
    static props = {
        defaultColor: { type: String, optional: true },
        selectedColor: { type: String, optional: true },
        noTransparency: { type: Boolean, optional: true },
        onColorSelect: { type: Function, optional: true },
        onColorPreview: { type: Function, optional: true },
        defaultOpacity: { type: Number, optional: true },
        setOnCloseCallback: { type: Function, optional: true },
        setOperationCallbacks: { type: Function, optional: true },
    };
    static defaultProps = {
        defaultColor: DEFAULT_COLOR,
        defaultOpacity: 100,
        noTransparency: false,
        onColorSelect: () => {},
        onColorPreview: () => {},
    };

    /** @type {"picker" | "slider" | "opacity" | null} */
    dragging = null;
    /** @type {number | null} */
    activePointerId = null;
    /** @type {Document[]} */
    draggedDocuments = [];

    setup() {
        this.defaultOpacity =
            this.props.defaultOpacity > 0 && this.props.defaultOpacity <= 1
                ? this.props.defaultOpacity * 100
                : this.props.defaultOpacity;
        this.defaultColor = this.props.defaultColor;
        if (/^#[0-9a-f]{6}$/i.test(this.defaultColor)) {
            const opacityHex = opacityToHex(this.defaultOpacity);
            this.defaultColor += opacityHex;
        }
        /** @type {Record<string, any>} */
        this.colorComponents = {};
        this.uniqueId = uniqueId("colorpicker");
        this.selectedHexValue = "";
        this.shouldSetSelectedColor = false;
        this.lastFocusedSliderEl = undefined;
        this.selectedColor = this.props.selectedColor || this.defaultColor;
        this.onPointerUp = this.onPointerUp.bind(this);
        this.onPointerCancel = this.onPointerCancel.bind(this);
        this.onEscapeKeydown = this.onEscapeKeydown.bind(this);

        this.elRef = useRef("el");
        this.hexInputRef = useRef("hexInput");
        this.colorPickerAreaRef = useRef("colorPickerArea");
        this.colorPickerPointerRef = useRef("colorPickerPointer");
        this.colorSliderRef = useRef("colorSlider");
        this.colorSliderPointerRef = useRef("colorSliderPointer");
        this.opacitySliderRef = useRef("opacitySlider");
        this.opacitySliderPointerRef = useRef("opacitySliderPointer");

        this.setupDragListeners();
        this.publishCallbacks();

        onMounted(() => {
            const rgba =
                convertCSSColorToRgba(this.selectedColor) ||
                convertCSSColorToRgba(this.defaultColor) ||
                DEFAULT_RGBA;
            this._updateRgba(rgba.red, rgba.green, rgba.blue, rgba.opacity);

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

    setupDragListeners() {
        this.throttleOnPointerMove = useThrottleForAnimation((ev) => {
            switch (this.dragging) {
                case "picker":
                    return this.onPointerMovePicker(ev);
                case "slider":
                    return this.onPointerMoveSlider(ev);
                case "opacity":
                    return this.onPointerMoveOpacitySlider(ev);
            }
        });
        this.onPointerMove = (ev) => {
            if (ev.pointerId === this.activePointerId) {
                return this.throttleOnPointerMove(ev);
            }
        };
        for (const doc of this.reachableDocuments()) {
            useExternalListener(
                doc,
                "keydown",
                /** @type {EventListener} */ (this.onEscapeKeydown),
                { capture: true },
            );
        }
        onWillUnmount(() => this.stopDrag());
    }

    /**
     * @param {"picker" | "slider" | "opacity"} kind
     * @param {PointerEvent} ev
     */
    startDrag(kind, ev) {
        if (ev.button !== 0 || this.dragging) {
            return false;
        }
        this.stopDrag();
        this.dragging = kind;
        this.activePointerId = ev.pointerId;
        this.draggedDocuments = this.reachableDocuments();
        for (const doc of this.draggedDocuments) {
            doc.addEventListener("pointermove", this.onPointerMove);
            doc.addEventListener("pointerup", this.onPointerUp);
            doc.addEventListener("pointercancel", this.onPointerCancel);
        }
        return true;
    }

    stopDrag() {
        this.throttleOnPointerMove.cancel();
        for (const doc of this.draggedDocuments) {
            doc.removeEventListener("pointermove", this.onPointerMove);
            doc.removeEventListener("pointerup", this.onPointerUp);
            doc.removeEventListener("pointercancel", this.onPointerCancel);
        }
        this.draggedDocuments = [];
        this.dragging = null;
        this.activePointerId = null;
    }

    /** @returns {Document[]} */
    reachableDocuments() {
        try {
            return [
                window.top,
                ...Array.from(window.top.frames).filter((frame) => {
                    try {
                        return !!frame.document;
                    } catch {
                        return false;
                    }
                }),
            ].map((w) => w.document);
        } catch {
            return [document];
        }
    }

    publishCallbacks() {
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
            onPreviewRevertCallback: () => {
                if (this.previewActive && this.shouldSetSelectedColor) {
                    this.props.onColorPreview(this.colorComponents);
                }
            },
        });
    }

    /** @param {string} color */
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
     * @returns {string[]}
     */
    getAllowedHotkeys(allowedKeys) {
        return allowedKeys.flatMap((key) => [key, `control+${key}`]);
    }
    /** @param {HTMLElement} el */
    setLastFocusedSliderEl(el) {
        this.lastFocusedSliderEl = el;
        /** @type {HTMLElement} */ (document.activeElement).blur();
    }

    get el() {
        return this.elRef.el;
    }

    /**
     * @param {PointerEvent} ev
     * @returns {{ x: number, y: number }}
     */
    getLocalPoint(ev) {
        const point = { x: ev.clientX, y: ev.clientY };
        const ownerView = this.elRef.el?.ownerDocument?.defaultView;
        let view =
            /** @type {any} */ (ev.view) ??
            /** @type {any} */ (ev.target)?.ownerDocument?.defaultView;
        if (!ownerView || !view) {
            return point;
        }
        try {
            while (view && view !== ownerView && view.frameElement) {
                const rect = view.frameElement.getBoundingClientRect();
                point.x += rect.left;
                point.y += rect.top;
                view = view.parent === view ? null : view.parent;
            }
        } catch {
            return { x: ev.clientX, y: ev.clientY };
        }
        return point;
    }
    /**
     * @param {string} hotkey
     * @param {number} value
     * @param {Object} [options]
     * @param {number} [options.min=0]
     * @param {number} [options.max=100]
     * @param {number} [options.defaultStep=10]
     * @param {number} [options.modifierStep=1]
     * @param {number} [options.leap=20]
     * @returns {number}
     */
    handleRangeKeydownValue(
        hotkey,
        value,
        { min = 0, max = 100, defaultStep = 10, modifierStep = 1, leap = 20 } = {},
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
    /** @param {String} hotkey */
    selectColorOnEnter(hotkey) {
        if (hotkey === "enter" && this.shouldSetSelectedColor) {
            this.stopDrag();
            this._colorSelected();
        }
    }

    /** @private */
    _updateUI() {
        const colorPickerArea = this.colorPickerAreaRef.el;
        const pickerHeight = colorPickerArea.clientHeight;
        const pickerWidth = colorPickerArea.clientWidth;
        const sliderHeight = this.colorSliderRef.el.clientHeight;
        const opacitySlider = this.props.noTransparency
            ? null
            : this.opacitySliderRef.el;
        const opacitySliderHeight = opacitySlider ? opacitySlider.clientHeight : 0;

        if (this.hexInputRef.el && this.hexInputRef.el !== document.activeElement) {
            /** @type {HTMLInputElement} */ (this.hexInputRef.el).value =
                this.colorComponents.hex;
        }

        colorPickerArea.style.backgroundColor = `hsl(${this.colorComponents.hue}, 100%, 50%)`;
        const top = ((100 - this.colorComponents.lightness) * pickerHeight) / 100;
        const left = (this.colorComponents.saturation * pickerWidth) / 100;

        const colorpickerPointer = this.colorPickerPointerRef.el;
        colorpickerPointer.style.top = `${top - 5}px`;
        colorpickerPointer.style.left = `${left - 5}px`;
        colorpickerPointer.setAttribute(
            "aria-label",
            _t("Saturation: %(saturationLvl)s %. Brightness: %(brightnessLvl)s %", {
                saturationLvl: this.colorComponents.saturation?.toFixed(2) || "0",
                brightnessLvl: this.colorComponents.lightness?.toFixed(2) || "0",
            }),
        );

        const y = (this.colorComponents.hue * sliderHeight) / 360;
        this.colorSliderPointerRef.el.style.bottom = `${Math.round(y - 4)}px`;
        this.colorSliderPointerRef.el.setAttribute(
            "aria-valuenow",
            this.colorComponents.hue.toFixed(2),
        );

        if (opacitySlider) {
            const z = opacitySliderHeight * (1 - this.colorComponents.opacity / 100.0);
            this.opacitySliderPointerRef.el.style.top = `${Math.round(z - 2)}px`;
            this.opacitySliderPointerRef.el.setAttribute(
                "aria-valuenow",
                this.colorComponents.opacity.toFixed(2),
            );

            const sliderColor = this.colorComponents.hex.slice(0, 7);
            opacitySlider.style.background = `linear-gradient(${sliderColor} 0%, transparent 100%)`;
        }
    }
    /**
     * @private
     * @param {string} hex
     */
    _updateHex(hex) {
        const rgb = convertCSSColorToRgba(hex);
        if (!rgb) {
            return;
        }
        const rgbToApply = { ...rgb };
        if (hex.replace("#", "").length !== 8) {
            delete rgbToApply.opacity;
        }
        Object.assign(
            this.colorComponents,
            rgbToApply,
            convertRgbToHsl(rgb.red, rgb.green, rgb.blue),
        );
        this.colorComponents.hex = convertRgbaToCSSColor(
            this.colorComponents.red,
            this.colorComponents.green,
            this.colorComponents.blue,
            this.colorComponents.opacity,
        );
        this._updateCssColor();
    }
    /**
     * @private
     * @param {number} r
     * @param {number} g
     * @param {number} b
     * @param {number} [a]
     */
    _updateRgba(r, g, b, a) {
        const opacity = a || this.colorComponents.opacity;
        if (opacity < 0.1 && (r > 0.1 || g > 0.1 || b > 0.1)) {
            a = this.defaultOpacity;
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
            convertRgbToHsl(r, g, b),
        );
        this._updateCssColor();
    }
    /**
     * @private
     * @param {number} h
     * @param {number} s
     * @param {number} l
     */
    _updateHsl(h, s, l) {
        if (0.1 < Math.abs(h - this.colorComponents.hue)) {
            if (l < 0.1 || 99.9 < l) {
                l = 50;
            }
            if (s < 0.1) {
                s = 100;
            }
        }
        let a = this.colorComponents.opacity;
        if (a < 0.1 && l > 0.1) {
            a = this.defaultOpacity;
        }

        const rgb = convertHslToRgb(h, s, l);
        if (!rgb) {
            return;
        }
        const hex = convertRgbaToCSSColor(rgb.red, rgb.green, rgb.blue, a);
        Object.assign(
            this.colorComponents,
            { hue: h, saturation: s, lightness: l },
            rgb,
            { hex: hex },
            { opacity: a },
        );
        this._updateCssColor();
    }
    /**
     * @private
     * @param {number} a
     */
    _updateOpacity(a) {
        if (a < 0 || a > 100) {
            return;
        }
        Object.assign(this.colorComponents, { opacity: a });
        const r = this.colorComponents.red;
        const g = this.colorComponents.green;
        const b = this.colorComponents.blue;
        Object.assign(this.colorComponents, {
            hex: convertRgbaToCSSColor(r, g, b, a),
        });
        this._updateCssColor();
    }
    /** @private */
    _colorSelected() {
        this.props.onColorSelect(this.colorComponents);
    }
    /** @private */
    _updateCssColor() {
        const r = this.colorComponents.red;
        const g = this.colorComponents.green;
        const b = this.colorComponents.blue;
        const a = this.colorComponents.opacity;
        Object.assign(this.colorComponents, {
            cssColor: convertRgbaToCSSColor(r, g, b, a),
        });
        if (this.previewActive) {
            this.props.onColorPreview(this.colorComponents);
        }
    }

    /**
     * @private
     * @param {KeyboardEvent} ev
     */
    onKeydown(ev) {
        if (ev.key === "Enter") {
            // the hex input applies on blur, not on a form submit
            ev.preventDefault();
        }
    }
    /** @param {MouseEvent} ev */
    onClick(ev) {
        const target = /** @type {HTMLInputElement} */ (ev.target);
        if (target.dataset.colorMethod === "hex" && !this.selectedHexValue) {
            target.select();
            this.selectedHexValue = target.value;
            return;
        }
        this.selectedHexValue = "";
    }
    /** @param {PointerEvent} ev */
    onPointerCancel(ev) {
        if (ev.pointerId === this.activePointerId) {
            log.logic("drag cancelled");
            this.stopDrag();
            this.lastFocusedSliderEl = undefined;
        }
    }
    /** @param {PointerEvent} ev */
    onPointerUp(ev) {
        if (ev.pointerId !== this.activePointerId) {
            return;
        }
        if (this.dragging) {
            this.shouldSetSelectedColor = true;
            this._updateCssColor();
        }
        this.stopDrag();

        if (this.lastFocusedSliderEl) {
            this.lastFocusedSliderEl.focus();
            this.lastFocusedSliderEl = undefined;
        }
    }
    /** @param {KeyboardEvent} ev */
    onEscapeKeydown(ev) {
        const hotkey = getActiveHotkey(ev);
        if (hotkey === "escape") {
            this.props.setOnCloseCallback?.(() => {});
        }
    }
    /**
     * @private
     * @param {PointerEvent} ev
     */
    onPointerDownPicker(ev) {
        if (!this.startDrag("picker", ev)) {
            return;
        }
        ev.preventDefault();
        this.onPointerMovePicker(ev);
        this.setLastFocusedSliderEl(this.colorPickerPointerRef.el);
    }
    /**
     * @private
     * @param {PointerEvent} ev
     */
    onPointerMovePicker(ev) {
        if (this.dragging !== "picker") {
            return;
        }

        const colorPickerArea = this.colorPickerAreaRef.el;
        const rect = colorPickerArea.getClientRects()[0];
        const { x, y } = this.getLocalPoint(ev);
        const top = y - rect.top;
        const left = x - rect.left;
        let saturation = Math.round((100 * left) / colorPickerArea.clientWidth);
        let lightness = Math.round(
            (100 * (colorPickerArea.clientHeight - top)) / colorPickerArea.clientHeight,
        );
        saturation = clamp(saturation, 0, 100);
        lightness = clamp(lightness, 0, 100);

        this._updateHsl(this.colorComponents.hue, saturation, lightness);
        this._updateUI();
    }
    /**
     * @private
     * @param {KeyboardEvent} ev
     */
    onPickerKeydown(ev) {
        const hotkey = getActiveHotkey(ev);
        this.selectColorOnEnter(hotkey);
        if (!this.getAllowedHotkeys(ARROW_KEYS).includes(hotkey)) {
            return;
        }
        const isVertical = ["arrowup", "arrowdown"].includes(
            hotkey.replace("control+", ""),
        );
        const { hue, saturation, lightness } = this.colorComponents;
        this._updateHsl(
            hue,
            isVertical ? saturation : this.handleRangeKeydownValue(hotkey, saturation),
            isVertical ? this.handleRangeKeydownValue(hotkey, lightness) : lightness,
        );
        this._updateUI();
        this.shouldSetSelectedColor = true;
    }
    /**
     * @private
     * @param {PointerEvent} ev
     */
    onPointerDownSlider(ev) {
        if (!this.startDrag("slider", ev)) {
            return;
        }
        ev.preventDefault();
        this.onPointerMoveSlider(ev);
        this.setLastFocusedSliderEl(this.colorSliderPointerRef.el);
    }
    /**
     * @private
     * @param {PointerEvent} ev
     */
    onPointerMoveSlider(ev) {
        if (this.dragging !== "slider") {
            return;
        }

        const colorSlider = this.colorSliderRef.el;
        const colorSliderRects = colorSlider.getClientRects();
        const y =
            colorSliderRects[0].height -
            (this.getLocalPoint(ev).y - colorSliderRects[0].top);
        let hue = Math.round((360 * y) / colorSlider.clientHeight);
        hue = clamp(hue, 0, 360);

        this._updateHsl(
            hue,
            this.colorComponents.saturation,
            this.colorComponents.lightness,
        );
        this._updateUI();
    }
    /** @param {KeyboardEvent} ev */
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
        this._updateHsl(
            hue,
            this.colorComponents.saturation,
            this.colorComponents.lightness,
        );
        this._updateUI();
        this.shouldSetSelectedColor = true;
    }
    /**
     * @private
     * @param {PointerEvent} ev
     */
    onPointerDownOpacitySlider(ev) {
        if (!this.startDrag("opacity", ev)) {
            return;
        }
        ev.preventDefault();
        this.onPointerMoveOpacitySlider(ev);
        this.setLastFocusedSliderEl(this.opacitySliderPointerRef.el);
    }
    /**
     * @private
     * @param {PointerEvent} ev
     */
    onPointerMoveOpacitySlider(ev) {
        if (this.dragging !== "opacity" || this.props.noTransparency) {
            return;
        }

        const opacitySlider = this.opacitySliderRef.el;
        const y = this.getLocalPoint(ev).y - opacitySlider.getClientRects()[0].top;
        let opacity = Math.round(100 * (1 - y / opacitySlider.clientHeight));
        opacity = clamp(opacity, 0, 100);

        this._updateOpacity(opacity);
        this._updateUI();
    }
    /** @param {KeyboardEvent} ev */
    onOpacitySliderKeydown(ev) {
        const hotkey = getActiveHotkey(ev);
        this.selectColorOnEnter(hotkey);
        if (!this.getAllowedHotkeys(SLIDER_KEYS).includes(hotkey)) {
            return;
        }
        const opacity = this.handleRangeKeydownValue(
            hotkey,
            this.colorComponents.opacity,
        );

        this._updateOpacity(opacity);
        this._updateUI();
        this.shouldSetSelectedColor = true;
    }
    /**
     * @private
     * @param {Event} ev
     */
    onHexColorInput(ev) {
        const hexColorValue = /** @type {HTMLInputElement} */ (
            ev.target
        ).value.replaceAll("#", "");
        if (hexColorValue.length === 6 || hexColorValue.length === 8) {
            this._updateHex(`#${hexColorValue}`);
            this._updateUI();
            this._colorSelected();
        }
    }
}
