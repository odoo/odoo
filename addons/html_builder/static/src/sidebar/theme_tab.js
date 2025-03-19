import { Component, useState } from "@odoo/owl";
import { OptionsContainer } from "./option_container";
import { useIsActiveItem } from "@html_builder/core/utils";
import { useOptionsSubEnv } from "@html_builder/utils/utils";

export class ThemeTab extends Component {
    static template = "html_builder.ThemeTab";
    static components = { OptionsContainer };
    static props = {
        // optionsContainers: { type: Array, optional: true },
    };
    static defaultProps = {
        // optionsContainers: [],
    };

    setup() {
        useOptionsSubEnv(() => [this.env.editor.document.body]);
        this.isActiveItem = useIsActiveItem();
        this.state = useState({
            fontsData: {},
        });
        this.optionsContainers = this.env.editor.resources["theme_options"];
    }
}
