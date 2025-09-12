import { Component } from "@odoo/owl";
import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";

class ColorPickerSolidTab extends Component {
    static template = "web.ColorPickerSolidTab";
    static props = {
        colorPickerNavigation: Function,
        onColorClick: Function,
        onColorPointerOver: Function,
        onColorPointerOut: Function,
        onFocusin: Function,
        onFocusout: Function,
        currentCustomColor: { type: String, optional: true },
        defaultColorSet: { type: String | Boolean, optional: true },
        themeColorPrefix: { type: String, optional: true },
        defaultColors: Array,
        defaultThemeColorVars: Array,
        "*": { optional: true },
    };
}

registry.category("color_picker_tabs").add("web.solid", {
    id: "solid",
    name: _t("Solid"),
    component: ColorPickerSolidTab,
});
