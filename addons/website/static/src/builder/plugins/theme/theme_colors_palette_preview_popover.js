import { Component } from "@odoo/owl";

export class ThemeColorsPalettePreviewPopover extends Component {
    static template = "website.ThemeColorsPalettePreviewPopover";
    static props = {
        palette: Object,
        close: { type: Function, optional: true },
    };
}

