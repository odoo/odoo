import { BaseOptionComponent } from "@html_builder/core/base_option_component";
import { HighlightThemeRowPlugin } from "@html_builder/core/building_blocks/highlight_theme_row_plugin";
import { usePlugin } from "@odoo/owl";

export class ThemeShadowOption extends BaseOptionComponent {
    static template = "website.ThemeShadowOption";

    setup() {
        super.setup();
        this.highlightThemeRow = usePlugin(HighlightThemeRowPlugin);
    }
}
