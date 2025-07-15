import { isColorGradient } from "@web/core/utils/colors";
import { Component, useState } from "@odoo/owl";
import {
    useColorPicker,
    DEFAULT_COLORS,
    DEFAULT_THEME_COLOR_VARS,
} from "@web/core/color_picker/color_picker";
import { effect } from "@web/core/utils/reactive";
import { toolbarButtonProps } from "../toolbar/toolbar";
import { getCSSVariableValue, getHtmlStyle } from "@html_editor/utils/formatting";

export class ColorSelector extends Component {
    static template = "html_editor.ColorSelector";
    static props = {
        ...toolbarButtonProps,
        mode: { type: String },
        type: { type: String },
        getSelectedColors: Function,
        applyColor: Function,
        applyColorPreview: Function,
        applyColorResetPreview: Function,
        getUsedCustomColors: Function,
        colorPrefix: { type: String },
        onClose: Function,
    };

    setup() {
        this.state = useState({});
        const htmlStyle = getHtmlStyle(document);
        const defaultThemeColors = DEFAULT_THEME_COLOR_VARS.map((color) =>
            getCSSVariableValue(color, htmlStyle)
        );
        this.solidColors = [
            ...DEFAULT_COLORS.flat(),
            ...defaultThemeColors,
            getCSSVariableValue("body-color", htmlStyle), // Default applied color
            "#00000000", //Default Background color
        ];
        effect(
            (selectedColors) => {
                this.state.selectedColor = selectedColors[this.props.mode];
                this.state.defaultTab = this.getCorrespondingColorTab(
                    selectedColors[this.props.mode]
                );
            },
            [this.props.getSelectedColors()]
        );

        this.colorPicker = useColorPicker(
            "root",
            {
                state: this.state,
                applyColor: this.props.applyColor,
                applyColorPreview: this.props.applyColorPreview,
                applyColorResetPreview: this.props.applyColorResetPreview,
                getUsedCustomColors: this.props.getUsedCustomColors,
                colorPrefix: this.props.colorPrefix,
            },
            {
                onClose: () => {
                    this.props.applyColorResetPreview();
                    this.props.onClose();
                },
            }
        );
    }

<<<<<<< ff569b56d147d73303826e6984af58579c4c6680
    getCorrespondingColorTab(color) {
        if (!color || this.solidColors.includes(color.toUpperCase())) {
            return "solid";
        } else if (isColorGradient(color)) {
            return "gradient";
        } else {
            return "custom";
||||||| d363c3ec467e494aa2c807d976fea7ef2502012b
    setTab(tab) {
        this.state.activeTab = tab;
    }

    processColorFromEvent(ev) {
        let color = ev.target.dataset.color;
        if (color && !isCSSColor(color) && !isColorGradient(color)) {
            color = (this.mode === "color" ? "text-" : "bg-") + color;
        }
        return color;
    }

    applyColor(color) {
        this.currentCustomColor.color = color;
        this.props.applyColor({ color: color || "", mode: this.mode });
        this.props.focusEditable();
    }

    onColorApply(ev) {
        if (ev.target.tagName !== "BUTTON") {
            return;
        }
        const color = this.processColorFromEvent(ev);
        this.applyColor(color);
        this.dropdown.close();
    }

    onColorPreview(ev) {
        const color = ev.hex ? ev.hex : this.processColorFromEvent(ev);
        this.props.applyColorPreview({ color: color || "", mode: this.mode });
    }

    onColorHover(ev) {
        if (ev.target.tagName !== "BUTTON") {
            return;
        }
        this.onColorPreview(ev);
    }

    onColorHoverOut(ev) {
        if (ev.target.tagName !== "BUTTON") {
            return;
        }
        this.props.applyColorResetPreview();
    }

    getCurrentGradientColor() {
        if (isColorGradient(this.selectedColors[this.mode])) {
            return this.selectedColors[this.mode];
=======
    setTab(tab) {
        this.state.activeTab = tab;
    }

    processColorFromEvent(ev) {
        let color = ev.target.dataset.color;
        if (color && !isCSSColor(color) && !isColorGradient(color)) {
            color = (this.mode === "color" ? "text-" : "bg-") + color;
        }
        return color;
    }

    applyColor(color) {
        this.currentCustomColor.color = color;
        this.props.applyColor({ color: color || "", mode: this.mode });
        this.props.focusEditable();
    }

    onColorApply(ev) {
        if (ev.target.tagName !== "BUTTON") {
            return;
        }
        const color = this.processColorFromEvent(ev);
        this.applyColor(color);
        this.dropdown.close();
    }

    onColorPreview(ev) {
        const color = ev.cssColor ? ev.cssColor : this.processColorFromEvent(ev);
        this.props.applyColorPreview({ color: color || "", mode: this.mode });
    }

    onColorHover(ev) {
        if (ev.target.tagName !== "BUTTON") {
            return;
        }
        this.onColorPreview(ev);
    }

    onColorHoverOut(ev) {
        if (ev.target.tagName !== "BUTTON") {
            return;
        }
        this.props.applyColorResetPreview();
    }

    getCurrentGradientColor() {
        if (isColorGradient(this.selectedColors[this.mode])) {
            return this.selectedColors[this.mode];
>>>>>>> bf85d5333e8afec48d7609210a127820cd2a5467
        }
    }

    getSelectedColorStyle() {
        if (isColorGradient(this.state.selectedColor)) {
            return `border-bottom: 2px solid transparent; border-image: ${this.state.selectedColor}; border-image-slice: 1`;
        }
        return `border-bottom: 2px solid ${this.state.selectedColor}`;
    }
}
