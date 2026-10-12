import { Component, proxy } from "@odoo/owl";
import { useOptionsSubEnv } from "@html_builder/utils/utils";
import { OptionsContainer } from "@html_builder/sidebar/option_container";

export class DesignTab extends Component {
    static template = "mass_mailing.DesignTab";
    static components = { OptionsContainer };

    setup() {
        useOptionsSubEnv(() => [this.env.editor.document.body]);
        this.state = proxy({
            fontsData: {},
        });
        this.optionsContainers = this.env.editor.resources["design_options"];
    }
}
