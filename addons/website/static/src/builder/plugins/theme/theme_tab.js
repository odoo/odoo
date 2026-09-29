import { OptionsContainer } from "@html_builder/sidebar/option_container";
import { useOptionsSubEnv } from "@html_builder/utils/utils";
import { Component, proxy, signal } from "@odoo/owl";

export class ThemeTab extends Component {
    static template = "website.ThemeTab";
    static components = { OptionsContainer };
    contentRef = signal.ref();

    setup() {
        useOptionsSubEnv(() => [this.env.editor.document.body]);
        this.state = proxy({
            fontsData: {},
        });
        this.optionsContainers = this.env.editor.resources["theme_options"];
    }
}
