import { Plugin, signal, t, useConfig } from "@odoo/owl";

export class HighlightThemeRowPlugin extends Plugin {
    openThemeTab = useConfig("openThemeTab", t.function());

    colorPresetToShow = signal(null);
    targetRowId = signal(null);

    openThemeOption = ({ presetId = null, targetRowId = null } = {}) => {
        this.setThemeReveal({ presetId, targetRowId });
        this.openThemeTab();
    };

    setThemeReveal({ presetId = null, targetRowId = null } = {}) {
        this.colorPresetToShow.set(presetId);
        this.targetRowId.set(targetRowId);
    }
}
