import { useSubEnv } from "@web/owl2/utils";
import { Component, props, proxy, t } from "@odoo/owl";
import { OptionsContainer } from "@html_builder/sidebar/option_container";
import { useOptionsSubEnv } from "@html_builder/utils/utils";

export class ThemeTab extends Component {
    static template = "website.ThemeTab";
    static components = { OptionsContainer };
    props = props({
        // optionsContainers: t.array().optional([]),
        colorPresetToShow: t.or([t.number(), t.literal(null)]).optional(),
        targetRowId: t.or([t.string(), t.literal(null)]).optional(),
        targetContainerId: t.or([t.string(), t.literal(null)]).optional(),
    });

    setup() {
        useOptionsSubEnv(() => [this.env.editor.document.body]);
        useSubEnv({
            colorPresetToShow: this.props.colorPresetToShow,
            targetRowId: this.props.targetRowId,
            targetContainerId: this.props.targetContainerId,
        });
        this.state = proxy({
            fontsData: {},
        });
        this.optionsContainers = this.env.editor.resources["theme_options"];
    }
}
