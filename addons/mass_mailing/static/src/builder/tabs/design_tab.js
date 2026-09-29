import { HighlightThemeRowPlugin } from "@html_builder/core/building_blocks/highlight_theme_row_plugin";
import { OptionsContainer } from "@html_builder/sidebar/option_container";
import { useOptionsSubEnv } from "@html_builder/utils/utils";
import { Component, proxy, usePlugin } from "@odoo/owl";

export class DesignTab extends Component {
    static template = "mass_mailing.DesignTab";
    static components = { OptionsContainer };

    setup() {
        useOptionsSubEnv(() => [this.env.editor.document.body]);
        this.highlightThemeRow = usePlugin(HighlightThemeRowPlugin);
        this.state = proxy({
            fontsData: {},
        });
        this.optionsContainers = this.env.editor.resources["design_options"];
    }
}
