import { Component, proxy, t, useProps } from "@odoo/owl";
import { useSubEnv } from "@web/owl2/utils";
import { useOptionsSubEnv } from "@html_builder/utils/utils";
import { OptionsContainer } from "@html_builder/sidebar/option_container";

export class DesignTab extends Component {
    static template = "mass_mailing.DesignTab";
    static components = { OptionsContainer };
    props = useProps({
        targetRowId: t.or([t.string(), t.literal(null)]).optional(),
    });

    setup() {
        useOptionsSubEnv(() => [this.env.editor.document.body]);
        useSubEnv({
            themeReveal: {
                targetRowId: this.props.targetRowId,
            },
        });
        this.state = proxy({
            fontsData: {},
        });
        this.optionsContainers = this.env.editor.resources["design_options"];
    }
}
