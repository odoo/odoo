import { Component } from "@odoo/owl";
import { WithSubEnv } from "../builder_helpers";
import { OptionsContainer } from "../components/OptionsContainer";

export class CustomizeTab extends Component {
    static template = "html_builder.CustomizeTab";
    static components = { WithSubEnv, OptionsContainer };
    static props = {
        currentOptionsContainers: { type: Object },
    };
}
