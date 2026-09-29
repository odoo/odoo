import { Plugin, signal } from "@odoo/owl";

export class HighlightThemeRowPlugin extends Plugin {
    colorPresetToShow = signal(null);
    targetRowId = signal(null);
}
