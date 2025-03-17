import { Component, onWillUpdateProps, useState } from "@odoo/owl";
import { Colorpicker } from "@web/core/colorpicker/colorpicker";
import { isColorGradient, rgbToHex } from "@html_editor/utils/color";

export class GradientPicker extends Component {
    static components = { Colorpicker };
    static template = "html_editor.GradientPicker";
    static props = {
        onGradientChange: { type: Function, optional: true },
        selectedGradient: { type: String, optional: true },
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
            { hex: "#FF00FF", percentage: 0 },
            { hex: "#00FFFF", percentage: 100 },
        ]);
        this.setGradientFromString(this.props.selectedGradient);

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
        const colors = [
            ...gradient.matchAll(
                /(#[0-9a-f]{6}|rgba?\(\s*[0-9]+\s*,\s*[0-9]+\s*,\s*[0-9]+\s*[,\s*[0-9.]*]?\s*\)|[a-z]+)\s*([[0-9]+%]?)/g
            ),
        ].filter((color) => rgbToHex(color[1]) !== "#");

        if (colors.length !== 2) {
            return;
        }

        this.colors[0] = { hex: rgbToHex(colors[0][1]), percentage: colors[0][2].replace("%", "") };
        this.colors[1] = { hex: rgbToHex(colors[1][1]), percentage: colors[1][2].replace("%", "") };

        const isLinear = gradient.startsWith("linear-gradient(");
        if (isLinear) {
            const angle = gradient.match(/([0-9]+)deg/);
            if (angle) {
                this.state.angle = angle[1];
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
    }

    selectType(type) {
        this.state.type = type;
        this.onColorGradientChange();
    }

    onAngleChange(ev) {
        this.state.angle = ev.target.value;
        this.onColorGradientChange();
    }

    onPositionChange(position, ev) {
        this.positions[position] = ev.target.value;
        this.onColorGradientChange();
    }

    onColorChange(color) {
        this.colors[this.state.currentColorIndex].hex = color.hex;
        this.onColorGradientChange();
    }

    onSizeChange(size) {
        this.state.size = size;
        this.onColorGradientChange();
    }

    onColorPercentageChange(colorIndex, ev) {
        this.state.currentColorIndex = colorIndex;
        this.colors[colorIndex].percentage = ev.target.value;
        if (this.colors[0].percentage > this.colors[1].percentage) {
            this.colors[1].percentage = this.colors[0].percentage;
        }
        this.onColorGradientChange();
    }

    onColorGradientChange() {
        if (this.state.type === "linear") {
            this.props.onGradientChange(
                `linear-gradient(${this.state.angle}deg, ${this.colors[0].hex} ${this.colors[0].percentage}%, ${this.colors[1].hex} ${this.colors[1].percentage}%)`
            );
        } else {
            this.props.onGradientChange(
                `radial-gradient(circle ${this.state.size} at ${this.positions.x}% ${this.positions.y}%, ${this.colors[0].hex} ${this.colors[0].percentage}%, ${this.colors[1].hex} ${this.colors[1].percentage}%)`
            );
        }
    }
}
