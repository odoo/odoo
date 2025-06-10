import { Component } from "@odoo/owl";
import { OptionsContainer } from "@html_builder/sidebar/option_container";
import { useOptionsSubEnv } from "@html_builder/utils/utils";

export class CustomizeTranslationTab extends Component {

    static template = "website.CustomizeTranslationTab";
    static components = { OptionsContainer };
    static props = {
        // optionsContainers: { type: Array, optional: true },
    };
    static defaultProps = {
        // optionsContainers: [],
    };

    setup() {
        useOptionsSubEnv(() => [this.env.editor.document.body]);
        this.optionsContainers = this.env.editor.resources["translate_options"];
    }

}
