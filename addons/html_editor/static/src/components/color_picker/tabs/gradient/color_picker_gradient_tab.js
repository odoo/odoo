import { useLayoutEffect } from "@web/owl2/utils";
import { Component, proxy, signal, t, useProps } from "@odoo/owl";
import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import { applyOpacityToGradient, isColorGradient } from "@web/core/utils/colors";
import { GradientPicker } from "../../gradient_picker/gradient_picker";

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
    props = useProps({
        applyColor: t.function(),
        onColorClick: t.function(),
        onColorPreview: t.function(),
        onColorPointerOver: t.function(),
        onColorPointerOut: t.function(),
        onFocusin: t.function(),
        onFocusout: t.function(),
        setOnCloseCallback: t.function().optional(),
        setOperationCallbacks: t.function().optional(),
        defaultOpacity: t.number().optional(),
        noTransparency: t.boolean().optional(),
        selectedColor: t.string().optional(),
        currentColorPreview: t.string().optional(),
    });

    customGradientButton = signal.ref();

    setup() {
        this.state = proxy({
            showGradientPicker: false,
        });
        this.applyOpacityToGradient = applyOpacityToGradient;
        this.DEFAULT_GRADIENT_COLORS = DEFAULT_GRADIENT_COLORS;
        useLayoutEffect(
            () => {
                if (this.state.showGradientPicker) {
                    this.customGradientButton()?.focus();
                }
            },
            () => [this.state.showGradientPicker]
        );
    }

    getCurrentGradientColor() {
        if (isColorGradient(this.props.currentColorPreview)) {
            return this.props.currentColorPreview;
        }
        if (isColorGradient(this.props.selectedColor)) {
            return this.props.selectedColor;
        }
    }

    toggleGradientPicker() {
        this.state.showGradientPicker = !this.state.showGradientPicker;
        if (
            !this.state.showGradientPicker &&
            this.props.currentColorPreview &&
            this.props.currentColorPreview !== this.props.selectedColor
        ) {
            this.props.applyColor(this.props.currentColorPreview);
        }
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
