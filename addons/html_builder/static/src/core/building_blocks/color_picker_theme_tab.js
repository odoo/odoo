import { Component } from "@odoo/owl";
import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";

export class ColorPickerThemeTab extends Component {
    static template = "html_builder.ColorPickerThemeTab";
    static props = {
        onColorClick: Function,
        onColorPointerOver: Function,
        onColorPointerOut: Function,
        onColorPointerLeave: Function,
        onFocusin: Function,
        onFocusout: Function,
        selectedColorCombination: { type: String, optional: true },
        "*": { optional: true },
    };
}

registry.category("color_picker_tabs").add(
    "html_builder.theme",
    {
        id: "theme",
        name: _t("Theme"),
        component: ColorPickerThemeTab,
    },
    { sequence: 10 }
);
