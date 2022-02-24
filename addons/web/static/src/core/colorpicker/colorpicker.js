/** @odoo-module */

import {
    convertCSSColorToRgba,
    convertRgbToHsl,
    convertHslToRgb,
    convertRGBToHEX,
} from "./colorpicker_utils";
import { clamp } from "@web/core/utils/numbers";

const { Component, useEffect, useState, useRef } = owl;

export class ColorPicker extends Component {
    setup() {
        this.state = useState({});
        this.unfocusPickers();

        useEffect(
            () => {
                const rgbColor = convertCSSColorToRgba(this.props.color || "#FF0000");
                const hslColor = convertRgbToHsl(rgbColor.red, rgbColor.green, rgbColor.blue);

                this.state.hue = hslColor.hue;
                this.state.saturation = hslColor.saturation;
                this.state.lightness = hslColor.lightness;

                this.state.opacity = this.props.transparency ? rgbColor.opacity : 100;

                // Latent colors are only updated when the hue is changed.
                this.state.latentHue = hslColor.hue;
                this.state.latentSaturation = hslColor.saturation;
                this.state.latentLightness = hslColor.lightness;

                this.updateUIFromState();
            },
            () => [this.props.color]
        );

        this.colorPickAreaRef = useRef("colorPickArea");
        this.colorPickAreaPointerRef = useRef("colorPickAreaPointer");
        this.colorSliderRef = useRef("colorSlider");
        this.colorSliderPointerRef = useRef("colorSliderPointer");
        this.colorOpacitySliderRef = useRef("colorOpacitySlider");
        this.colorOpacitySliderPointerRef = useRef("colorOpacitySliderPointer");
    }

    updateColorState(h, s, l, a, updateLatent = false) {
        // validation
        h = clamp(h, 0, 360);
        s = clamp(s, 0, 100);
        l = clamp(l, 0, 100);
        a = clamp(a, 0, 100);

        this.state.hue = h;
        this.state.saturation = s;
        this.state.lightness = l;
        this.state.opacity = a;
        if (updateLatent) {
            this.state.latentHue = h;
            this.state.latentSaturation = s;
            this.state.latentLightness = l;
        }

        this.props.onColorSelected({
            hue: this.state.hue,
            saturation: this.state.saturation,
            lightness: this.state.lightness,
            opacity: this.state.opacity,
            red: this.red,
            blue: this.blue,
            green: this.green,
            hex: this.hex,
        });
    }

    updateUIFromState() {
        // Color pick
        let bounds = this.colorPickAreaRef.el.getBoundingClientRect();
        let top = clamp(Math.round((this.state.lightness / 100) * bounds.height), 0, bounds.height);
        let left = clamp(Math.round((this.state.saturation / 100) * bounds.width), 0, bounds.width);
        this.moveColorPickAreaPointer(left, top);

        // Hue slider
        bounds = this.colorSliderRef.el.getBoundingClientRect();
        top = clamp(Math.round((this.state.hue / 360) * bounds.height), 0, bounds.height);
        this.moveColorSliderPointer(top);

        // Opacity slider
        if (this.props.transparency) {
            bounds = this.colorOpacitySliderRef.el.getBoundingClientRect();
            top = clamp(Math.round((this.state.opacity / 100) * bounds.height), 0, bounds.height);
            this.moveColorOpacitySliderPointer(bounds.height - top);
        }
    }

    unfocusPickers() {
        this.isPickingColor = false;
        this.isSlidingHue = false;
        this.isSlidingOpacity = false;
    }

    get red() {
        return convertHslToRgb(this.state.hue, this.state.saturation, this.state.lightness).red;
    }
    get green() {
        return convertHslToRgb(this.state.hue, this.state.saturation, this.state.lightness).green;
    }
    get blue() {
        return convertHslToRgb(this.state.hue, this.state.saturation, this.state.lightness).blue;
    }
    get hex() {
        const rgb = convertHslToRgb(this.state.hue, this.state.saturation, this.state.lightness);
        return convertRGBToHEX(rgb.red, rgb.green, rgb.blue);
    }

    // =============== Color Pick Area ===============
    onMouseMoveColorPickArea(ev) {
        if (this.isPickingColor) {
            this.handleColorPickAreaEvent(ev);
        }
    }
    onMouseDownColorPickArea(ev) {
        this.handleColorPickAreaEvent(ev);
        this.isPickingColor = true;
    }
    handleColorPickAreaEvent(ev) {
        const bounds = this.colorPickAreaRef.el.getBoundingClientRect();
        const top = clamp(ev.pageY - bounds.top, 0, bounds.height);
        const left = clamp(ev.pageX - bounds.left, 0, bounds.width);
        this.moveColorPickAreaPointer(left, top);
        const saturation = clamp(Math.round((100 * left) / bounds.width), 0, 100);
        const lightness = clamp(Math.round((100 * (bounds.height - top)) / bounds.height), 0, 100);
        this.updateColorState(this.state.hue, saturation, lightness, this.state.opacity);
    }
    moveColorPickAreaPointer(x, y) {
        const bounds = this.colorPickAreaPointerRef.el.getBoundingClientRect();
        this.colorPickAreaPointerRef.el.style.left = `${x - bounds.width / 2}px`;
        this.colorPickAreaPointerRef.el.style.top = `${y - bounds.height / 2}px`;
    }

    // =============== Color Slider Area ===============
    onMouseMoveColorSlider(ev) {
        if (this.isSlidingHue) {
            this.handleColorSliderEvent(ev);
        }
    }
    onMouseDownColorSlider(ev) {
        this.handleColorSliderEvent(ev);
        this.isSlidingHue = true;
    }
    handleColorSliderEvent(ev) {
        const bounds = this.colorSliderRef.el.getBoundingClientRect();
        const top = clamp(ev.pageY - bounds.top, 0, bounds.height);
        this.moveColorSliderPointer(top);
        const hue = clamp(Math.round(360 * (top / bounds.height)), 0, 360);
        this.updateColorState(
            hue,
            this.state.saturation,
            this.state.lightness,
            this.state.opacity,
            true
        );
    }
    moveColorSliderPointer(y) {
        const bounds = this.colorSliderPointerRef.el.getBoundingClientRect();
        this.colorSliderPointerRef.el.style.top = `${y - bounds.height / 4}px`;
    }

    // =============== Opacity Slider Area ===============
    onMouseMoveColorOpacitySlider(ev) {
        if (this.isSlidingOpacity) {
            this.handleColorOpacitySliderEvent(ev);
        }
    }
    onMouseDownColorOpacitySlider(ev) {
        this.handleColorOpacitySliderEvent(ev);
        this.isSlidingOpacity = true;
    }
    handleColorOpacitySliderEvent(ev) {
        const bounds = this.colorOpacitySliderRef.el.getBoundingClientRect();
        const top = clamp(ev.pageY - bounds.top, 0, bounds.height);
        this.moveColorOpacitySliderPointer(top);
        const opacity = clamp(Math.round((100 * (bounds.height - top)) / bounds.height), 0, 100);
        this.updateColorState(this.state.hue, this.state.saturation, this.state.lightness, opacity);
    }
    moveColorOpacitySliderPointer(y) {
        const bounds = this.colorOpacitySliderPointerRef.el.getBoundingClientRect();
        this.colorOpacitySliderPointerRef.el.style.top = `${y - bounds.height / 4}px`;
    }

    // Inputs Handling
    onInputChangeRed(ev) {
        let newRed = +ev.target.value;
        if (isNaN(newRed)) {
            ev.target.value = this.red;
        } else {
            const tmp = newRed;
            newRed = clamp(newRed, 0, 255);
            if (newRed != tmp) {
                ev.target.value = newRed;
            }
            const hslColor = convertRgbToHsl(newRed, this.green, this.blue);
            this.updateColorState(
                hslColor.hue,
                hslColor.saturation,
                hslColor.lightness,
                this.state.opacity,
                true
            );
            this.updateUIFromState();
        }
    }
    onInputChangeGreen(ev) {
        let newGreen = +ev.target.value;
        if (isNaN(newGreen)) {
            ev.target.value = this.green;
        } else {
            const tmp = newGreen;
            newGreen = clamp(newGreen, 0, 255);
            if (newGreen != tmp) {
                ev.target.value = newGreen;
            }
            const hslColor = convertRgbToHsl(this.red, newGreen, this.blue);
            this.updateColorState(
                hslColor.hue,
                hslColor.saturation,
                hslColor.lightness,
                this.state.opacity,
                true
            );
            this.updateUIFromState();
        }
    }
    onInputChangeBlue(ev) {
        let newBlue = +ev.target.value;
        if (isNaN(newBlue)) {
            ev.target.value = this.blue;
        } else {
            const tmp = newBlue;
            newBlue = clamp(newBlue, 0, 255);
            if (newBlue != tmp) {
                ev.target.value = newBlue;
            }
            const hslColor = convertRgbToHsl(this.red, this.green, newBlue);
            this.updateColorState(
                hslColor.hue,
                hslColor.saturation,
                hslColor.lightness,
                this.state.opacity,
                true
            );
            this.updateUIFromState();
        }
    }
    onInputChangeOpacity(ev) {
        const newOpacity = +ev.target.value;
        if (isNaN(newOpacity)) {
            ev.target.value = this.state.opacity;
        } else {
            this.updateColorState(
                this.state.hue,
                this.state.saturation,
                this.state.lightness,
                newOpacity,
                true
            );
            this.updateUIFromState();
        }
    }
    onInputChangeHex(ev) {
        let rgbColor;
        let invalid = false;
        try {
            rgbColor = convertCSSColorToRgba(ev.target.value);
            rgbColor.opacity = this.props.transparency ? rgbColor.opacity : 100;
        } catch (e) {
            invalid = true;
            ev.target.value = this.hex;
        }
        if (!invalid) {
            const hslColor = convertRgbToHsl(rgbColor.red, rgbColor.green, rgbColor.blue);
            this.updateColorState(
                hslColor.hue,
                hslColor.saturation,
                hslColor.lightness,
                rgbColor.opacity,
                true
            );
            this.updateUIFromState();
        }
    }
}

ColorPicker.template = "web.ColorPicker";
ColorPicker.props = {
    color: { type: String, optional: true },
    onColorSelected: Function,
    transparency: { type: Boolean, optional: true },
    showPreview: { type: Boolean, optional: true },
};
ColorPicker.defaultProps = {
    color: "#000000",
    transparency: false,
    showPreview: true,
};
