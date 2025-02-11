import { isColorGradient } from "@web/core/utils/colors";
import { Component, useState } from "@odoo/owl";
import { useColorPicker } from "@web/core/color_picker/color_picker";
import { effect } from "@web/core/utils/reactive";
import { toolbarButtonProps } from "../toolbar/toolbar";

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
    };

    setup() {
        this.state = useState({});
        effect(
            (selectedColors) => {
                this.state.selectedColor = selectedColors[this.props.mode];
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
            { onClose: () => this.props.applyColorResetPreview() }
        );
    }

    getSelectedColorStyle() {
        if (isColorGradient(this.state.selectedColor)) {
            return `border-bottom: 2px solid transparent; border-image: ${this.state.selectedColor}; border-image-slice: 1`;
        }
        return `border-bottom: 2px solid ${this.state.selectedColor}`;
    }
}
