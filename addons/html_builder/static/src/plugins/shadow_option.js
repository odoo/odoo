import { BaseOptionComponent } from "@html_builder/core/base_option_component";
import { HighlightThemeRowPlugin } from "@html_builder/sidebar/highlight_theme_row_plugin";
import { t, usePlugin, useProps } from "@odoo/owl";

export class ShadowOption extends BaseOptionComponent {
    static template = "html_builder.ShadowOption";
    props = useProps({
        setShadowClassAction: t.string().optional("setShadowClass"),
        setShadowModeAction: t.string().optional("setShadowMode"),
        setShadowStyleAction: t.string().optional("setShadowStyle"),
    });

    setup() {
        super.setup();
        this.highlightThemeRow = usePlugin(HighlightThemeRowPlugin);
    }

    getEditAction(shadowClass) {
        return {
            onClick: () => this.highlightThemeRow.openThemeOption({ targetRowId: shadowClass }),
        };
    }
}
