import { useBuilderComponents, useIsActiveItem } from "@html_builder/core/utils";
import { getBgImageURLFromEl, normalizeColor } from "@html_builder/utils/utils_css";
import { Component } from "@odoo/owl";

export class BackgroundImageOption extends Component {
    static template = "html_builder.BackgroundImageOption";
    static props = {};
    setup() {
        useBuilderComponents();
        this.isActiveItem = useIsActiveItem();
    }
    showMainColorPicker() {
        const editingEl = this.env.getEditingElement();
        const src = new URL(getBgImageURLFromEl(editingEl), window.location.origin);
        return (
            src.origin === window.location.origin &&
            (src.pathname.startsWith("/html_editor/shape/") ||
                src.pathname.startsWith("/web_editor/shape/"))
        );
    }
    getColorPickerColorNames() {
        const colorNames = [];
        const editingEl = this.env.getEditingElement();
        for (let nbr = 1; nbr <= 5; nbr++) {
            const colorName = `c${nbr}`;
            if (getBackgroundImageColor(editingEl, colorName)) {
                colorNames.push(colorName);
            }
        }
        return colorNames;
    }
}

export function getBackgroundImageColor(editingEl, colorName) {
    const backgroundImageColor = new URL(
        getBgImageURLFromEl(editingEl),
        window.location.origin
    ).searchParams.get(colorName);
    if (backgroundImageColor) {
        return normalizeColor(backgroundImageColor);
    }
}
