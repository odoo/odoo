import { Component, onWillUpdateProps, useState, useRef } from "@odoo/owl";
import { CustomColorPicker as ColorPicker } from "@web/core/color_picker/custom_color_picker/custom_color_picker";
import {
    isColorGradient,
    standardizeGradient,
    rgbaToHex,
    convertCSSColorToRgba,
} from "@web/core/utils/colors";

export class GradientPicker extends Component {
    static components = { ColorPicker };
    static template = "html_editor.GradientPicker";
    static props = {
        onGradientChange: { type: Function, optional: true },
        onGradientPreview: { type: Function, optional: true },
        setOnCloseCallback: { type: Function, optional: true },
        setOperationCallbacks: { type: Function, optional: true },
        selectedGradient: { type: String, optional: true },
        noTransparency: { type: Boolean, optional: true },
    };

    setup() {
        this.state = useState({
            type: "linear",
            angle: 135,
            currentColorIndex: 0,
            size: "closest-side",
        });
        this.positions = useState({ x: 25, y: 25 });
        this.colors = useState([
            { hex: "#DF7CC4", percentage: 0 },
            { hex: "#6C3582", percentage: 100 },
        ]);
        this.cssGradients = useState({ preview: "", linear: "", radial: "", sliderThumbStyle: "" });
        this.knobRef = useRef("gradientAngleKnob");

        if (this.props.selectedGradient && isColorGradient(this.props.selectedGradient)) {
            // initialization of the gradient with the selected value
            this.setGradientFromString(this.props.selectedGradient);
        } else {
            // initialization of the gradient with default value
            this.onColorGradientChange();
        }

        onWillUpdateProps((newProps) => {
            if (newProps.selectedGradient) {
                this.setGradientFromString(newProps.selectedGradient);
            }
        });
    }

    setGradientFromString(gradient) {
        if (!gradient || !isColorGradient(gradient)) {
            return;
        }
        gradient = standardizeGradient(gradient);
        const colors = [
            ...gradient.matchAll(
                /(#[0-9a-f]{6}|rgba?\(\s*[0-9]+\s*,\s*[0-9]+\s*,\s*[0-9]+\s*[,\s*[0-9.]*]?\s*\)|[a-z]+)\s*([[0-9]+%]?)/g
            ),
        ].filter((color) => rgbaToHex(color[1]) !== "#");

        this.colors.splice(0, this.colors.length);
        for (const color of colors) {
            this.colors.push({ hex: rgbaToHex(color[1]), percentage: color[2].replace("%", "") });
        }

        const isLinear = gradient.startsWith("linear-gradient(");
        if (isLinear) {
            const angle = gradient.match(/(-?[0-9]+)deg/);
            if (angle) {
                this.state.angle = parseInt(angle[1]);
            }
        } else {
            this.state.type = "radial";
            const sizeMatch = gradient.match(/(closest|farthest)-(side|corner)/);
            const size = sizeMatch ? sizeMatch[0] : "farthest-corner";
            this.state.size = size;

            const position = gradient.match(/ at ([0-9]+)% ([0-9]+)%/) || ["", "50", "50"];
            this.positions.x = position[1];
            this.positions.y = position[2];
        }

        this.updateCssGradients();
    }

    selectType(type) {
        this.state.type = type;
        this.onColorGradientChange();
    }

    onAngleChange(ev) {
        const angle = parseInt(ev.target.value);
        if (!isNaN(angle)) {
            const clampedAngle = Math.min(Math.max(angle, 0), 360);
            ev.target.value = clampedAngle;
            this.state.angle = clampedAngle;
            this.onColorGradientChange();
        }
    }

    onPositionChange(position, ev) {
        const inputValue = parseFloat(ev.target.value);
        if (!isNaN(inputValue)) {
            const clampedValue = Math.min(Math.max(inputValue, 0), 100);
            ev.target.value = clampedValue;
            this.positions[position] = clampedValue;
            this.onColorGradientChange();
        }
    }

    onColorChange(color) {
        const hex = rgbaToHex(color.cssColor);
        this.colors[this.state.currentColorIndex].hex = hex;
        this.onColorGradientChange();
    }

    onColorPreview(color) {
        const hex = rgbaToHex(color.cssColor);
        this.colors[this.state.currentColorIndex].hex = hex;
        this.onColorGradientPreview();
    }

    onSizeChange(size) {
        this.state.size = size;
        this.onColorGradientChange();
    }

    onColorPercentageChange(colorIndex, ev) {
        this.state.currentColorIndex = colorIndex;
        this.colors[colorIndex].percentage = ev.target.value;
        this.sortColors();
        this.onColorGradientChange();
    }

    onGradientPreviewClick(ev) {
        const width = parseInt(window.getComputedStyle(ev.target).width, 10);
        const percentage = Math.round((100 * ev.offsetX) / width);
        this.addColorStop(percentage);
    }

    addColorStop(percentage) {
        let color;

        let previousColor = this.colors.findLast((color) => color.percentage <= percentage);
        let nextColor = this.colors.find((color) => color.percentage > percentage);
        if (!previousColor && nextColor) {
            // Click position is before the first color
            color = nextColor.hex;
        } else if (!nextColor && previousColor) {
            //  Click position is after the last color
            color = previousColor.hex;
        } else if (nextColor && previousColor) {
            const previousRatio =
                (nextColor.percentage - percentage) /
                (nextColor.percentage - previousColor.percentage);
            const nextRatio = 1 - previousRatio;

            previousColor = convertCSSColorToRgba(previousColor.hex);
            nextColor = convertCSSColorToRgba(nextColor.hex);

            const red = Math.round(previousRatio * previousColor.red + nextRatio * nextColor.red);
            const green = Math.round(
                previousRatio * previousColor.green + nextRatio * nextColor.green
            );
            const blue = Math.round(
                previousRatio * previousColor.blue + nextRatio * nextColor.blue
            );
            const opacity = Math.round(
                previousRatio * previousColor.opacity + nextRatio * nextColor.opacity
            );
            color = `rgba(${red}, ${green}, ${blue}, ${opacity / 100})`;
        }

        this.colors.push({ hex: color, percentage });
        this.sortColors();
        this.state.currentColorIndex = this.colors.findIndex(
            (color) => color.percentage === percentage
        );
        this.onColorGradientChange();
    }

    removeColor(colorIndex) {
        if (this.colors.length <= 2) {
            return;
        }
        this.colors.splice(colorIndex, 1);
        this.state.currentColorIndex = 0;
        this.onColorGradientChange();
    }

    sortColors() {
        this.colors = this.colors.sort((a, b) => a.percentage - b.percentage);
    }

    updateCssGradients() {
        const gradientColors = this.colors
            .map((color) => `${color.hex} ${color.percentage}%`)
            .join(", ");
        let sliderThumbStyle = "";
        // color the slider thumb with the color of the gradient
        for (let i = 0; i < this.colors.length; i++) {
            const selector = `.gradient-colors div:nth-child(${i + 1}) input[type="range"]`;
            const style = `background-color: ${this.colors[i].hex};`;
            sliderThumbStyle += `${selector}::-webkit-slider-thumb { ${style} }\n`;
            sliderThumbStyle += `${selector}::-moz-range-thumb { ${style} }\n`;
        }

        this.cssGradients.preview = `linear-gradient(90deg, ${gradientColors})`;
        this.cssGradients.linear = `linear-gradient(${this.state.angle}deg, ${gradientColors})`;
        this.cssGradients.radial = `radial-gradient(circle ${this.state.size} at ${this.positions.x}% ${this.positions.y}%, ${gradientColors})`;
        this.cssGradients.sliderThumbStyle = sliderThumbStyle;
    }

    onColorGradientChange() {
        this.updateCssGradients();
        this.props?.onGradientChange(this.cssGradients[this.state.type]);
    }

    onColorGradientPreview() {
        this.updateCssGradients();
        this.props.onGradientPreview?.({ gradient: this.cssGradients[this.state.type] });
    }

    get currentColorHex() {
        return this.colors?.[this.state.currentColorIndex]?.hex || "#000000";
    }

    onKnobMouseDown(ev) {
        const knobEl = this.knobRef.el;
        if (!knobEl) {
            return;
        }
        const knobRadius = knobEl.offsetWidth / 2;
        const knobRect = knobEl.getBoundingClientRect();
        const centerX = knobRect.left + knobRadius;
        const centerY = knobRect.top + knobRadius;

        const updateAngle = (ev) => {
            // calculate the differences between the mouse position and the
            // center of the knob
            const distanceX = ev.clientX - centerX;
            const distanceY = ev.clientY - centerY;

            // calculate the angle between the center and the mouse position
            const angle = Math.atan2(distanceY, distanceX) * (180 / Math.PI);
            this.state.angle = Math.round((angle + 360) % 360);
        };

        updateAngle(ev);
        this.onColorGradientChange();

        const onKnobMouseMove = (ev) => {
            updateAngle(ev);
            this.onColorGradientChange();
        };
        const onKnobMouseUp = () => document.removeEventListener("mousemove", onKnobMouseMove);

        document.addEventListener("mousemove", onKnobMouseMove);
        document.addEventListener("mouseup", onKnobMouseUp, { once: true });
    }
}
