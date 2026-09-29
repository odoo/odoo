import { BaseOptionComponent } from "@html_builder/core/base_option_component";
import { ThemeRevealPlugin } from "@html_builder/core/building_blocks/theme_reveal_plugin";
import { usePlugin } from "@odoo/owl";

export class ThemeShadowOption extends BaseOptionComponent {
    static template = "website.ThemeShadowOption";

    setup() {
        super.setup();
        this.themeReveal = usePlugin(ThemeRevealPlugin);
    }
}
