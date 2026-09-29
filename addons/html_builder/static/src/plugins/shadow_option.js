import { BaseOptionComponent } from "@html_builder/core/base_option_component";
import { HighlightThemeRowPlugin } from "@html_builder/sidebar/highlight_theme_row_plugin";
import { t, usePlugin, useProps } from "@odoo/owl";
import { _t } from "@web/core/l10n/translation";

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
            title: _t("Edit in Theme Tab"),
            onClick: () => this.highlightThemeRow.editThemeOption(shadowClass),
        };
    }
}
