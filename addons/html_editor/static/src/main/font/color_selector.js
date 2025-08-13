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
        enabledTabs: { type: Array, optional: true },
        themeColorPrefix: { type: String, optional: true },
        onClose: Function,
    };
    static defaultProps = {
        themeColorPrefix: "",
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
                enabledTabs: this.props.enabledTabs,
                themeColorPrefix: this.props.themeColorPrefix,
            },
            {
                onClose: () => {
                    this.props.applyColorResetPreview();
                    this.props.onClose();
                },
            }
        );
    }

    getCorrespondingColorTab(color) {
        if (!color || this.solidColors.includes(color.toUpperCase())) {
            return "solid";
        } else if (isColorGradient(color)) {
            return "gradient";
        } else {
            return "custom";
        }
    }

    getSelectedColorStyle() {
        if (isColorGradient(this.state.selectedColor)) {
            return `border-bottom: 2px solid transparent; border-image: ${this.state.selectedColor}; border-image-slice: 1`;
        }
        return `border-bottom: 2px solid ${this.state.selectedColor}`;
    }
}
