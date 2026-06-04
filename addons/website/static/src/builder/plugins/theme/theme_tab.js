import { useSubEnv } from "@web/owl2/utils";
import { Component, proxy } from "@odoo/owl";
import { OptionsContainer } from "@html_builder/sidebar/option_container";
import { useOptionsSubEnv } from "@html_builder/utils/utils";

export class ThemeTab extends Component {
    static template = "website.ThemeTab";
    static components = { OptionsContainer };
    static props = {
        // optionsContainers: { type: Array, optional: true },
        colorPresetToShow: { type: [Number, { value: null }], optional: true },
        shadowSizeToShow: { type: [String, { value: null }], optional: true },
    };
    static defaultProps = {
        // optionsContainers: [],
    };

    setup() {
        useOptionsSubEnv(() => [this.env.editor.document.body]);
        useSubEnv({
            colorPresetToShow: this.props.colorPresetToShow,
            shadowSizeToShow: this.props.shadowSizeToShow,
        });
        this.state = proxy({
            fontsData: {},
        });
        this.optionsContainers = this.env.editor.resources["theme_options"];
    }
}
