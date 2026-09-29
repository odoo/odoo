import { Plugin, t, useConfig } from "@odoo/owl";

export class ThemeRevealPlugin extends Plugin {
    colorPresetToShow = useConfig(
        "colorPresetToShow",
        t.or([t.number(), t.literal(null)]).optional()
    );
    targetRowId = useConfig("targetRowId", t.or([t.string(), t.literal(null)]).optional());

    clearTargetRow() {
        this.targetRowId = null;
    }
}
