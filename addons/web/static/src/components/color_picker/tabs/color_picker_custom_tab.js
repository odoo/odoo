// @ts-check

/** @module @web/components/color_picker/tabs/color_picker_custom_tab - Color picker tab for custom color input with gradient support */

import { Component } from "@odoo/owl";
import { CustomColorPicker } from "@web/components/color_picker/custom_color_picker/custom_color_picker";
import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import { isColorGradient } from "@web/core/utils/format/colors";
export class ColorPickerCustomTab extends Component {
    static template = "web.ColorPickerCustomTab";
    static components = { CustomColorPicker };
    static props = {
        applyColor: Function,
        colorPickerNavigation: Function,
        onColorClick: Function,
        onColorPreview: Function,
        onColorPointerOver: Function,
        onColorPointerOut: Function,
        onFocusin: Function,
        onFocusout: Function,
        getUsedCustomColors: { type: Function, optional: true },
        currentColorPreview: { type: String, optional: true },
        currentCustomColor: { type: String, optional: true },
        defaultColorSet: { type: [String, Boolean], optional: true },
        defaultOpacity: { type: Number, optional: true },
        grayscales: { type: Object, optional: true },
        cssVarColorPrefix: { type: String, optional: true },
        noTransparency: { type: Boolean, optional: true },
        setOnCloseCallback: { type: Function, optional: true },
        setOperationCallbacks: { type: Function, optional: true },
        "*": { optional: true },
    };

    setup() {
        /** @type {string[]} */
        this.usedCustomColors = this.props.getUsedCustomColors();
    }

    /**
     * Check whether a color is valid for the custom palette (non-transparent, non-gradient).
     * @param {string} color - hex color string
     * @returns {boolean}
     */
    isValidCustomColor(color) {
        return color && color.slice(7, 9) !== "00" && !isColorGradient(color);
    }
}

registry.category("color_picker_tabs").add("web.custom", {
    id: "custom",
    name: _t("Custom"),
    component: ColorPickerCustomTab,
});
