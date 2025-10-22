import { Component, useState } from "@odoo/owl";
import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import { applyOpacityToGradient, isColorGradient } from "@web/core/utils/colors";
import { GradientPicker } from "./gradient_picker/gradient_picker";

const DEFAULT_GRADIENT_COLORS = [
    "linear-gradient(135deg, rgb(255, 204, 51) 0%, rgb(226, 51, 255) 100%)",
    "linear-gradient(135deg, rgb(102, 153, 255) 0%, rgb(255, 51, 102) 100%)",
    "linear-gradient(135deg, rgb(47, 128, 237) 0%, rgb(178, 255, 218) 100%)",
    "linear-gradient(135deg, rgb(203, 94, 238) 0%, rgb(75, 225, 236) 100%)",
    "linear-gradient(135deg, rgb(214, 255, 127) 0%, rgb(0, 179, 204) 100%)",
    "linear-gradient(135deg, rgb(255, 222, 69) 0%, rgb(69, 33, 0) 100%)",
    "linear-gradient(135deg, rgb(222, 222, 222) 0%, rgb(69, 69, 69) 100%)",
    "linear-gradient(135deg, rgb(255, 222, 202) 0%, rgb(202, 115, 69) 100%)",
];

export class ColorPickerGradientTab extends Component {
    static template = "html_editor.ColorPickerGradientTab";
    static components = { GradientPicker };
    static props = {
        applyColor: Function,
        onColorClick: Function,
        onColorPreview: Function,
        onColorPointerOver: Function,
        onColorPointerOut: Function,
        onFocusin: Function,
        onFocusout: Function,
        setOnCloseCallback: { type: Function, optional: true },
        setOperationCallbacks: { type: Function, optional: true },
        defaultOpacity: { type: Number, optional: true },
        noTransparency: { type: Boolean, optional: true },
        selectedColor: { type: String, optional: true },
        "*": { optional: true },
    };
    setup() {
        this.state = useState({
            showGradientPicker: false,
        });
        this.applyOpacityToGradient = applyOpacityToGradient;
        this.DEFAULT_GRADIENT_COLORS = DEFAULT_GRADIENT_COLORS;
    }

    getCurrentGradientColor() {
        if (isColorGradient(this.props.selectedColor)) {
            return this.props.selectedColor;
        }
    }

    toggleGradientPicker() {
        this.state.showGradientPicker = !this.state.showGradientPicker;
    }
}

registry.category("color_picker_tabs").add(
    "html_editor.gradient",
    {
        id: "gradient",
        name: _t("Gradient"),
        component: ColorPickerGradientTab,
    },
    { sequence: 60 }
);
