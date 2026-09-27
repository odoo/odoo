import { Component, signal, t, useProps } from "@odoo/owl";
import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";

export class ColorPickerSolidTab extends Component {
    static template = "html_editor.ColorPickerSolidTab";

    solidTabRef = signal.ref();

    props = useProps({
        colorPickerNavigation: t.function(),
        onColorClick: t.function(),
        onColorPointerOver: t.function(),
        onColorPointerOut: t.function(),
        onFocusin: t.function(),
        onFocusout: t.function(),
        currentCustomColor: t.string().optional(),
        defaultColorSet: t.or([t.string(), t.boolean()]).optional(),
        cssVarColorPrefix: t.string().optional(),
        defaultColors: t.array(),
        defaultThemeColorVars: t.array(),
    });
}

registry.category("color_picker_tabs").add(
    "html_editor.solid",
    {
        id: "solid",
        name: _t("Solid"),
        component: ColorPickerSolidTab,
    },
    { sequence: 40 }
);
