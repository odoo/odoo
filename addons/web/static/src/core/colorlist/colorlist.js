import { _t } from "@web/core/l10n/translation";

import { Component, t, useProps } from "@odoo/owl";

export class ColorList extends Component {
    static COLORS = [
        _t("No color"),
        _t("Red"),
        _t("Orange"),
        _t("Yellow"),
        _t("Cyan"),
        _t("Purple"),
        _t("Almond"),
        _t("Teal"),
        _t("Blue"),
        _t("Raspberry"),
        _t("Green"),
        _t("Violet"),
    ];
    static template = "web.ColorList";
    props = useProps({
        disableTransparent: t.boolean().optional(),
        onColorSelected: t.function(),
        selectedColor: t.number().optional(),
    });
    get colors() {
        return this.constructor.COLORS;
    }
    onColorSelected(id) {
        this.props.onColorSelected(id);
    }
}
