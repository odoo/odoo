import { Component, useState } from "@odoo/owl";
import { OptionsContainer } from "./option_container";
import { useOptionsSubEnv } from "@html_builder/utils/utils";

export class DesignTab extends Component {
    static template = "mass_mailing_egg.DesignTab";
    static components = { OptionsContainer };

    setup() {
        useOptionsSubEnv(() => [this.env.editor.document.body]);
        this.state = useState({
            fontsData: {},
        });
        this.optionsContainers = this.env.editor.resources["design_options"];
    }
}
