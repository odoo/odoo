import { Component, useProps, t } from "@odoo/owl";
import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";

export class ColorPickerThemeTab extends Component {
    static template = "html_builder.ColorPickerThemeTab";
    props = useProps({
        onColorClick: t.function(),
        onColorPointerOver: t.function(),
        onColorPointerOut: t.function(),
        onColorPointerLeave: t.function(),
        onFocusin: t.function(),
        onFocusout: t.function(),
        selectedColorCombination: t.string().optional(),
        editColorCombination: t.function().optional(),
        close: t.function().optional(),
    });
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
