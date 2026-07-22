import { Component, props, t } from "@odoo/owl";

export class ThemeColorsPalettePreviewPopover extends Component {
    static template = "website.ThemeColorsPalettePreviewPopover";
    props = props({
        palette: t.object(),
        close: t.function().optional(),
    });
}

