import { Component, useState } from "@odoo/owl";
import { OptionsContainer } from "@html_builder/sidebar/option_container";
import { useOptionsSubEnv } from "@html_builder/utils/utils";

export class ThemeTab extends Component {
    static template = "website.ThemeTab";
    static components = { OptionsContainer };
    static props = {
        // optionsContainers: { type: Array, optional: true },
    };
    static defaultProps = {
        // optionsContainers: [],
    };

    setup() {
        useOptionsSubEnv(() => [this.env.editor.document.body]);
        this.state = useState({
            fontsData: {},
        });
        this.optionsContainers = this.env.editor.resources["theme_options"];
    }
}
