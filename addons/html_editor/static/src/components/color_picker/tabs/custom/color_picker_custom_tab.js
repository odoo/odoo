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
        close: t.function().optional(),
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
        this.allUsedCustomColors = Array.from(this.props.getUsedCustomColors()).filter(isCSSColor);
    }

    get usedColors() {
        const { currentCustomColor, currentColorPreview, defaultColorSet } = this.props;
        const isSameColor = (c1, c2) => c1?.toLowerCase() === c2?.toLowerCase();

        const colors = this.allUsedCustomColors.filter(
            (color) =>
                !isSameColor(color, currentCustomColor) && !isSameColor(color, currentColorPreview)
        );
        const additionalColors = [];
        if (!defaultColorSet && this.isValidCustomColor(currentCustomColor)) {
            additionalColors.push(currentCustomColor);
        }
        if (currentColorPreview && !isSameColor(additionalColors[0], currentColorPreview)) {
            additionalColors.push(currentColorPreview);
        }
        // Keep one slot free for the color to be previewed.
        const freeSlot = currentColorPreview ? 0 : 1;
        const availableSlots = MAX_USED_COLORS_TO_SHOW - additionalColors.length - freeSlot;
        return [...colors.slice(0, Math.max(0, availableSlots)), ...additionalColors];
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
