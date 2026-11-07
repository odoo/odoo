import { HighlightThemeRowPlugin } from "@html_builder/sidebar/highlight_theme_row_plugin";
import { Component, t, usePlugin, useProps } from "@odoo/owl";
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
        close: t.function().optional(),
    });

    setup() {
        super.setup();
        this.highlightThemeRow = usePlugin(HighlightThemeRowPlugin);
    }
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
