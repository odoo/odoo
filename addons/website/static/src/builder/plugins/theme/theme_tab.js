import { ThemeRevealPlugin } from "@html_builder/core/building_blocks/theme_reveal_plugin";
import { OptionsContainer } from "@html_builder/sidebar/option_container";
import { useOptionsSubEnv } from "@html_builder/utils/utils";
import { Component, providePlugins, proxy, signal, t, useProps } from "@odoo/owl";

export class ThemeTab extends Component {
    static template = "website.ThemeTab";
    static components = { OptionsContainer };
    props = useProps({
        // optionsContainers: t.array().optional([]),
        colorPresetToShow: t.or([t.number(), t.literal(null)]).optional(),
        targetRowId: t.or([t.string(), t.literal(null)]).optional(),
    });
    contentRef = signal.ref();

    setup() {
        useOptionsSubEnv(() => [this.env.editor.document.body]);
        providePlugins([ThemeRevealPlugin], {
            colorPresetToShow: this.props.colorPresetToShow,
            targetRowId: this.props.targetRowId,
        });
        this.state = proxy({
            fontsData: {},
        });
        this.optionsContainers = this.env.editor.resources["theme_options"];
    }
}
