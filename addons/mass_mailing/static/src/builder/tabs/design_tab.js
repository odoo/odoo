import { ThemeRevealPlugin } from "@html_builder/core/building_blocks/theme_reveal_plugin";
import { OptionsContainer } from "@html_builder/sidebar/option_container";
import { useOptionsSubEnv } from "@html_builder/utils/utils";
import { Component, providePlugins, proxy, t, useProps } from "@odoo/owl";

export class DesignTab extends Component {
    static template = "mass_mailing.DesignTab";
    static components = { OptionsContainer };
    props = useProps({
        targetRowId: t.or([t.string(), t.literal(null)]).optional(),
    });

    setup() {
        useOptionsSubEnv(() => [this.env.editor.document.body]);
        providePlugins([ThemeRevealPlugin], { targetRowId: this.props.targetRowId });
        this.state = proxy({
            fontsData: {},
        });
        this.optionsContainers = this.env.editor.resources["design_options"];
    }
}
