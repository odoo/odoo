import { Component, t, useProps } from "@odoo/owl";
import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import { isColorGradient, isCSSColor } from "@web/core/utils/colors";
import { CustomColorPicker } from "../../custom_color_picker/custom_color_picker";

const MAX_USED_COLORS_TO_SHOW = 16;

export class ColorPickerCustomTab extends Component {
    static template = "html_editor.ColorPickerCustomTab";
    static components = { CustomColorPicker };
    props = useProps({
        applyColor: t.function(),
        colorPickerNavigation: t.function(),
        onColorClick: t.function(),
        onColorPreview: t.function(),
        onColorPointerOver: t.function(),
        onColorPointerOut: t.function(),
        onFocusin: t.function(),
        onFocusout: t.function(),
        getUsedCustomColors: t.function().optional(),
        currentColorPreview: t.string().optional(),
        currentCustomColor: t.string().optional(),
        defaultColorSet: t.or([t.string(), t.boolean()]).optional(),
        defaultOpacity: t.number().optional(),
        grayscales: t.object().optional(),
        cssVarColorPrefix: t.string().optional(),
        noTransparency: t.boolean().optional(),
        setOnCloseCallback: t.function().optional(),
        setOperationCallbacks: t.function().optional(),
    });

    setup() {
        this.usedCustomColors = Array.from(this.props.getUsedCustomColors()).filter(isCSSColor);
    }

    get usedColors() {
        const colors = this.usedCustomColors.filter(
            (color) => color.toLowerCase() !== this.props.currentCustomColor?.toLowerCase()
        );
        const additionalColors =
            (!this.props.defaultColorSet && this.isValidCustomColor(this.props.currentCustomColor)
                ? 1
                : 0) + (this.props.currentColorPreview ? 1 : 0);

        return colors.slice(0, MAX_USED_COLORS_TO_SHOW - additionalColors);
    }

    isValidCustomColor(color) {
        return color && color.slice(7, 9) !== "00" && !isColorGradient(color);
    }
}

registry.category("color_picker_tabs").add(
    "html_editor.custom",
    {
        id: "custom",
        name: _t("Custom"),
        component: ColorPickerCustomTab,
    },
    { sequence: 50 }
);
